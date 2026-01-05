"""
Service for asynchronously executing RAG experiments in the background.

This module handles the execution of RAG experiments by:
1. Running RAG searches for each test case across multiple RAG configurations
2. Executing evaluations on the RAG search outputs
3. Updating experiment and test case statuses throughout execution
"""

import json
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from pydantic import TypeAdapter

if TYPE_CHECKING:
    from schemas.internal_schemas import RagSearchSettingConfigurationTypes

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from clients.rag_providers.rag_client_constructor import RagClientConstructor
from db_models.rag_experiment_models import (
    DatabaseRagExperiment,
    DatabaseRagExperimentTestCase,
    DatabaseRagExperimentTestCaseRagResult,
)
from repositories.datasets_repository import DatasetRepository
from repositories.rag_experiment_repository import RagExperimentRepository
from repositories.rag_providers_repository import RagProvidersRepository
from schemas.base_experiment_schemas import (
    EvalResultSummary,
    TestCaseStatus,
)
from schemas.rag_experiment_schemas import (
    RagConfig,
    RagEvalResultSummaries,
    RagSummaryResults,
)
from schemas.request_schemas import (
    RagHybridSearchSettingRequest,
    RagKeywordSearchSettingRequest,
    RagVectorSimilarityTextSearchSettingRequest,
)
from schemas.response_schemas import RagProviderQueryResponse
from services.experiment_executor import BaseExperimentExecutor

logger = logging.getLogger(__name__)


# TypeAdapter for RagConfig: RagConfig is a type alias (Annotated[Union[...], Discriminator(...)])
# not a BaseModel, so it doesn't have model_validate(). TypeAdapter allows us to validate
# discriminated union types that aren't Pydantic models.
RagConfigAdapter = TypeAdapter(RagConfig)


class RagExperimentExecutor(BaseExperimentExecutor):
    """Handles execution of RAG experiments"""

    def __init__(self) -> None:
        super().__init__()

    def _get_database_experiment(
        self,
        experiment_id: str,
        session: Session,
    ) -> Optional[DatabaseRagExperiment]:
        rag_experiment_repo = RagExperimentRepository(session)
        try:
            return rag_experiment_repo._get_db_experiment(experiment_id)
        except HTTPException:
            logger.error(f"Rag experiment with ID {experiment_id} not found.")
            return None

    def _get_db_test_cases(
        self,
        experiment_id: str,
        db_session: Session,
        status_filter: Optional[TestCaseStatus] = None,
    ) -> List[DatabaseRagExperimentTestCase]:
        rag_experiment_repo = RagExperimentRepository(db_session)
        return rag_experiment_repo._get_db_test_cases(experiment_id, status_filter)

    def _get_db_test_case(
        self,
        test_case_id: str,
        db_session: Session,
    ) -> Optional[DatabaseRagExperimentTestCase]:
        rag_experiment_repo = RagExperimentRepository(db_session)
        return rag_experiment_repo._get_db_test_case(test_case_id)

    def _execute_experiment_outputs(
        self,
        db_session: Session,
        test_case: DatabaseRagExperimentTestCase,
        request_time_parameters: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Execute all RAG searches for a test case.

        Args:
            db_session: Database session
            test_case: Test case to execute RAG searches for
            request_time_parameters: Optional dict of request-time parameters (not used for RAG experiments)

        Returns:
            True if all RAG searches executed successfully, False otherwise
        """
        any_rag_failed = False
        for rag_result in test_case.rag_results:
            success = self._execute_rag_search(db_session, rag_result, test_case)
            if not success:
                any_rag_failed = True
                logger.warning(
                    f"RAG search {rag_result.rag_config_key} failed in test case {test_case.id}, continuing with other searches",
                )
        return not any_rag_failed

    def _calculate_total_test_case_cost(
        self,
        test_case: DatabaseRagExperimentTestCase,
    ) -> float:
        """
        Calculate the total cost for a RAG test case.
        Note: RAG searches don't have cost tracking, so we only sum eval costs.

        Args:
            test_case: Test case to calculate cost for

        Returns:
            Total cost as a float
        """
        total_cost = 0.0
        for rag_result in test_case.rag_results:
            # Add eval costs
            total_cost += self._calculate_total_cost_eval_scores(rag_result.eval_scores)
        return total_cost

    def _resolve_rag_configuration(
        self,
        rag_result: DatabaseRagExperimentTestCaseRagResult,
        experiment: DatabaseRagExperiment,
        rag_providers_repo: RagProvidersRepository,
    ) -> Optional[
        Tuple[
            "RagSearchSettingConfigurationTypes",
            UUID,
            RagConfig,
        ]
    ]:
        """
        Resolve and validate RAG configuration components for a RAG result.

        This method handles both saved and unsaved RAG configurations by:
        1. Retrieving settings configuration and provider ID based on config type
        2. Finding the RAG config from experiment configuration
        3. Validating all required components are present

        Args:
            rag_result: RAG result containing configuration metadata
            experiment: RAG experiment containing configuration definitions
            rag_providers_repo: Repository for accessing RAG provider data

        Returns:
            Tuple of (settings_config, rag_provider_id, rag_config)
            if all components are successfully resolved, None otherwise
        """
        settings_config = None
        rag_provider_id = None
        rag_config = None

        if rag_result.rag_config_type == "saved":
            # Use repository method to get setting configuration version
            try:
                setting_version = (
                    rag_providers_repo.get_rag_setting_configuration_version(
                        rag_result.setting_configuration_id,
                        rag_result.setting_configuration_version,
                        include_deleted_versions=False,
                    )
                )
            except HTTPException as e:
                logger.error(
                    f"RAG setting configuration version not found: {e.detail}",
                )
                return None

            settings_config = setting_version.settings
            if not settings_config:
                # happens when settings config was soft deleted - should never be reached but
                # keeping the fallback
                logger.error(
                    f"RAG setting configuration version has no settings",
                )
                return None

            # Get setting configuration so we have the RAG provider ID available
            try:
                setting_config_obj = rag_providers_repo.get_rag_setting_configuration(
                    rag_result.setting_configuration_id,
                )
            except HTTPException as e:
                logger.error(
                    f"RAG setting configuration not found: {e.detail}",
                )
                return None

            if not setting_config_obj.rag_provider_id:
                # happens when setting config was soft-deleted - should never be reached but keeping
                # the fallback
                logger.error(
                    f"RAG setting configuration has no provider configured",
                )
                return None

            rag_provider_id = setting_config_obj.rag_provider_id

            # Find the RAG config - used later to get the query_column
            for config_dict in experiment.rag_configs:
                if (
                    str(config_dict.get("setting_configuration_id"))
                    == str(rag_result.setting_configuration_id)
                    and config_dict.get("version")
                    == rag_result.setting_configuration_version
                ):
                    rag_config = RagConfigAdapter.validate_python(config_dict)
                    break

        elif rag_result.rag_config_type == "unsaved":
            # Find the unsaved config by UUID from rag_config_key
            if not rag_result.rag_config_key.startswith("unsaved:"):
                logger.error(
                    f"Invalid unsaved RAG config key format: {rag_result.rag_config_key}",
                )
                return None

            unsaved_id_str = rag_result.rag_config_key.split(":", 1)[1]
            for config_dict in experiment.rag_configs:
                if (
                    config_dict.get("type") == "unsaved"
                    and str(config_dict.get("unsaved_id")) == unsaved_id_str
                ):
                    rag_config = RagConfigAdapter.validate_python(config_dict)
                    settings_config = rag_config.settings
                    rag_provider_id = rag_config.rag_provider_id
                    break
        else:
            logger.error(f"Unknown RAG config type: {rag_result.rag_config_type}")
            return None

        if not rag_config:
            logger.error(
                f"RAG config not found for {rag_result.rag_config_key}",
            )
            return None

        if not settings_config:
            logger.error(
                f"RAG config {rag_result.rag_config_key} has no settings",
            )
            return None

        if not rag_provider_id:
            logger.error(
                f"RAG config {rag_result.rag_config_key} has no provider ID",
            )
            return None

        return (settings_config, rag_provider_id, rag_config)

    def _execute_rag_search(
        self,
        db_session: Session,
        rag_result: DatabaseRagExperimentTestCaseRagResult,
        test_case: DatabaseRagExperimentTestCase,
    ) -> bool:
        """
        Execute a single RAG search and save the output.

        Args:
            db_session: Database session
            rag_result: RAG result record to populate
            test_case: Test case containing input variables

        Returns:
            True if RAG search executed successfully, False otherwise
        """
        try:
            experiment = test_case.experiment
            rag_providers_repo = RagProvidersRepository(db_session)
            dataset_repo = DatasetRepository(db_session)

            # Resolve RAG configuration components needed to run the search
            config_result = self._resolve_rag_configuration(
                rag_result,
                experiment,
                rag_providers_repo,
            )
            if not config_result:
                return False

            settings_config, rag_provider_id, rag_config = config_result

            # Get RAG provider configuration
            try:
                rag_provider_config = rag_providers_repo.get_rag_provider_configuration(
                    rag_provider_id,
                )
            except HTTPException as e:
                logger.error(
                    f"RAG provider {rag_provider_id} not found: {e.detail}",
                )
                return False

            # Extract query text from the dataset row
            query_text = self._extract_query_text(
                dataset_repo,
                experiment,
                test_case,
                rag_config,
            )
            if not query_text:
                return False

            # Save extracted query text in config object
            rag_result.query_text = query_text
            db_session.commit()

            # Construct and execute the search request
            request = settings_config.to_client_request_model(query_text)

            # Execute search using the Rag client
            rag_client_constructor = RagClientConstructor(rag_provider_config)
            response = self._execute_rag_search_request(
                rag_client_constructor,
                request,
            )
            if not response:
                return False

            # Save output to result object
            rag_result.search_output = response.model_dump(mode="json")
            db_session.commit()

            logger.info(
                f"Executed RAG search {rag_result.rag_config_key} for test case {test_case.id}",
            )
            return True

        except Exception as e:
            logger.error(
                f"Error executing RAG search {rag_result.rag_config_key}: {e}",
                exc_info=True,
            )
            return False

    def _extract_query_text(
        self,
        dataset_repo: DatasetRepository,
        experiment: DatabaseRagExperiment,
        test_case: DatabaseRagExperimentTestCase,
        rag_config: RagConfig,
    ) -> Optional[str]:
        """
        Extract query text from a dataset row using the RAG config's query column.

        Args:
            dataset_repo: Dataset repository instance
            experiment: RAG experiment containing dataset information
            test_case: Test case containing the dataset row ID
            rag_config: RAG configuration containing query column information

        Returns:
            Query text string if found, None otherwise
        """
        try:
            dataset_row = dataset_repo.get_dataset_version_row(
                experiment.dataset_id,
                experiment.dataset_version,
                UUID(test_case.dataset_row_id),
            )
        except HTTPException as e:
            logger.error(
                f"Dataset row not found: {e.detail}",
            )
            return None

        # Extract query text from the dataset row using query_column
        query_column_name = rag_config.query_column.dataset_column.name
        query_text = ""
        if dataset_row.data and query_column_name in dataset_row.data:
            query_value = dataset_row.data[query_column_name]
            query_text = str(query_value) if query_value is not None else ""

        if not query_text:
            logger.error(
                f"No query text found in dataset row {test_case.dataset_row_id} for column '{query_column_name}'",
            )
            return None

        return query_text

    def _execute_rag_search_request(
        self,
        rag_client_constructor: RagClientConstructor,
        request: Union[
            RagVectorSimilarityTextSearchSettingRequest,
            RagKeywordSearchSettingRequest,
            RagHybridSearchSettingRequest,
        ],
    ) -> Optional[RagProviderQueryResponse]:
        """
        Execute a RAG search request using the appropriate method.

        Args:
            rag_client_constructor: RAG client constructor
            request: Search request object

        Returns:
            Query response or None if execution failed
        """
        try:
            if isinstance(request, RagVectorSimilarityTextSearchSettingRequest):
                return rag_client_constructor.execute_similarity_text_search(request)
            elif isinstance(request, RagKeywordSearchSettingRequest):
                return rag_client_constructor.execute_keyword_search(request)
            elif isinstance(request, RagHybridSearchSettingRequest):
                return rag_client_constructor.execute_hybrid_search(request)
            else:
                logger.error(f"Unknown request type: {type(request)}")
                return None
        except Exception as e:
            logger.error(
                f"Error executing RAG search request: {e}",
                exc_info=True,
            )
            return None

    def _execute_evaluations(
        self,
        db_session: Session,
        test_case: DatabaseRagExperimentTestCase,
    ) -> bool:
        """
        Execute all evaluations for a RAG test case.

        Args:
            db_session: Database session
            test_case: Test case containing RAG results to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        try:
            any_eval_failed = False
            for rag_result in test_case.rag_results:
                success = self._execute_evaluations_for_result(db_session, rag_result)
                if not success:
                    any_eval_failed = True
                    logger.warning(
                        f"Evaluations failed for RAG config {rag_result.rag_config_key} in test case {test_case.id}, continuing with other evaluations",
                    )
            return not any_eval_failed
        except Exception as e:
            logger.error(
                f"Error executing evaluations for test case {test_case.id}: {e}",
                exc_info=True,
            )
            return False

    def _execute_evaluations_for_result(
        self,
        db_session: Session,
        rag_result: DatabaseRagExperimentTestCaseRagResult,
    ) -> bool:
        """
        Execute all evaluations for a RAG result.

        Args:
            db_session: Database session
            rag_result: RAG result with output to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        try:
            # Execute all eval scores using the relationship, tracking failures but continuing
            any_eval_failed = False
            for eval_score in rag_result.eval_scores:
                success = self._execute_single_eval(
                    db_session,
                    eval_score,
                    rag_result,
                )
                if not success:
                    any_eval_failed = True
                    logger.warning(
                        f"Eval {eval_score.eval_name} v{eval_score.eval_version} failed for RAG result {rag_result.id}, continuing with other evals",
                    )

            return not any_eval_failed

        except Exception as e:
            logger.error(
                f"Error executing evaluations for RAG result {rag_result.id}: {e}",
                exc_info=True,
            )
            return False

    def _process_experiment_output_variable(
        self,
        test_case_result: DatabaseRagExperimentTestCaseRagResult,
        variable_name: str,
        json_path: Optional[str],
    ) -> str:
        """
        Extract the value for an experiment_output variable from a RAG result.

        Args:
            test_case_result: RAG result with output
            variable_name: Name of the variable to extract
            json_path: Optional JSON path to extract a specific value from the search output

        Returns:
            The extracted value as a string
            If json_path is provided, extracts that specific value; otherwise returns full JSON
        """
        if not test_case_result.search_output:
            logger.warning("No search output included at this stage in the experiment.")
            return ""

        # Use JSON path extraction if provided, otherwise return full response as JSON
        if json_path:
            return self._extract_value_from_json_path(
                test_case_result.search_output,
                json_path,
                default=json.dumps(test_case_result.search_output, indent=2),
            )

        # No json_path provided, return full response as JSON string
        return json.dumps(test_case_result.search_output, indent=2)

    def _set_summary_results(
        self,
        db_session: Session,
        experiment: DatabaseRagExperiment,
    ) -> None:
        """
        Calculate summary results for an experiment based on completed test cases.

        Args:
            db_session: Database session
            experiment: DatabaseRagExperiment object

        Sets summary results dictionary with rag_eval_summaries
        """
        try:
            # Get all completed test cases with their RAG results and eval scores
            test_cases = self._get_db_test_cases(
                experiment.id,
                db_session,
                TestCaseStatus.COMPLETED,
            )

            if not test_cases:
                experiment.summary_results = RagSummaryResults(
                    rag_eval_summaries=[],
                ).model_dump(
                    mode="json",
                    exclude_none=True,
                )
                return

            # Build a structure to aggregate results: {rag_config_key: {(eval_name, eval_version): [scores]}}
            results_by_rag_config: dict[
                str,
                dict[tuple[str, int], list[float]],
            ] = {}

            for test_case in test_cases:
                for rag_result in test_case.rag_results:
                    rag_config_key = rag_result.rag_config_key

                    if rag_config_key not in results_by_rag_config:
                        results_by_rag_config[rag_config_key] = {}

                    for eval_score in rag_result.eval_scores:
                        eval_key = (eval_score.eval_name, eval_score.eval_version)

                        if eval_key not in results_by_rag_config[rag_config_key]:
                            results_by_rag_config[rag_config_key][eval_key] = []

                        # Add the score if eval result exists
                        if eval_score.eval_result_score is not None:
                            results_by_rag_config[rag_config_key][eval_key].append(
                                eval_score.eval_result_score,
                            )

            # Build the summary structure using Pydantic models
            rag_eval_summaries = []
            for rag_config_key, eval_results in sorted(results_by_rag_config.items()):
                # Parse rag_config_key to get components
                # For saved: "saved:setting_config_id:version"
                # For unsaved: "unsaved:uuid"
                parts = rag_config_key.split(":")
                if len(parts) >= 3 and parts[0] == "saved":
                    # Saved config
                    setting_configuration_id = UUID(parts[1])
                    setting_configuration_version = int(parts[2])
                    rag_config_type = "saved"
                elif len(parts) >= 2 and parts[0] == "unsaved":
                    # Unsaved config - UUID is in parts[1]
                    rag_config_type = "unsaved"
                    setting_configuration_id = None
                    setting_configuration_version = None
                else:
                    # Warn for unexpected format
                    logger.warning(
                        f"Unexpected RAG config key format: {rag_config_key}",
                    )
                    continue

                eval_result_list = []
                for (eval_name, eval_version), scores in sorted(eval_results.items()):
                    # Count how many passed (score >= 0.5, assuming 0-1 scale)
                    pass_count = sum(1 for s in scores if s >= 0.5)
                    total_count = len(scores)

                    eval_result_list.append(
                        EvalResultSummary(
                            eval_name=eval_name,
                            eval_version=str(eval_version),
                            pass_count=pass_count,
                            total_count=total_count,
                        ),
                    )

                rag_eval_summaries.append(
                    RagEvalResultSummaries(
                        rag_config_key=rag_config_key,
                        rag_config_type=rag_config_type,
                        setting_configuration_id=setting_configuration_id,
                        setting_configuration_version=setting_configuration_version,
                        eval_results=eval_result_list,
                    ),
                )

            experiment.summary_results = RagSummaryResults(
                rag_eval_summaries=rag_eval_summaries,
            ).model_dump(mode="json", exclude_none=True)

        except Exception as e:
            logger.error(
                f"Error calculating summary results for RAG experiment {experiment.id}: {e}",
                exc_info=True,
            )
            experiment.summary_results = RagSummaryResults(
                rag_eval_summaries=[],
            ).model_dump(
                mode="json",
                exclude_none=True,
            )
