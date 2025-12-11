import logging
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session, joinedload

from db_models.dataset_models import (
    DatabaseDataset,
    DatabaseDatasetVersion,
    DatabaseDatasetVersionRow,
)
from db_models.llm_eval_models import DatabaseLLMEval
from db_models.rag_experiment_models import (
    DatabaseRagExperiment,
    DatabaseRagExperimentTestCase,
    DatabaseRagExperimentTestCaseRagResult,
    DatabaseRagExperimentTestCaseRagResultEvalScore,
)
from db_models.rag_provider_models import (
    DatabaseRagProviderConfiguration,
    DatabaseRagSearchSettingConfiguration,
    DatabaseRagSearchSettingConfigurationVersion,
)
from db_models.task_models import DatabaseTask
from schemas.base_experiment_schemas import (
    DatasetRef,
    DatasetRefInput,
    EvalExecution,
    EvalExecutionResult,
    EvalRef,
    ExperimentStatus,
    InputVariable,
    TestCaseStatus,
)
from schemas.common_schemas import NewDatasetVersionRowColumnItemRequest
from schemas.internal_schemas import (
    WeaviateHybridSearchSettingsConfiguration,
    WeaviateKeywordSearchSettingsConfiguration,
    WeaviateVectorSimilarityTextSearchSettingsConfiguration,
)
from schemas.rag_experiment_schemas import (
    CreateRagExperimentRequest,
    RagConfig,
    RagConfigResponse,
    RagConfigResult,
    RagExperimentDetail,
    RagExperimentSummary,
    RagResult,
    RagSearchOutput,
    RagSummaryResults,
    RagTestCase,
    SavedRagConfig,
    UnsavedRagConfig,
    UnsavedRagConfigResponse,
)
from schemas.request_schemas import (
    WeaviateHybridSearchSettingsConfigurationRequest,
    WeaviateKeywordSearchSettingsConfigurationRequest,
    WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
)
from schemas.response_schemas import RagProviderQueryResponse

logger = logging.getLogger(__name__)

# TypeAdapter for RagConfig: RagConfig is a type alias (Annotated[Union[...], Discriminator(...)])
# not a BaseModel, so it doesn't have model_validate(). TypeAdapter allows us to validate
# discriminated union types that aren't Pydantic models.
RagConfigAdapter = TypeAdapter(RagConfig)
RagConfigResponseAdapter = TypeAdapter(RagConfigResponse)


class RagExperimentRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _convert_rag_config_to_response(
        self,
        config: RagConfig,
    ) -> RagConfigResponse:
        """Convert a RagConfig (with request types) to RagConfigResponse (with response types)"""
        if config.type == "saved":
            # Saved configs don't need conversion - they're the same in both request and response
            return SavedRagConfig(
                type="saved",
                setting_configuration_id=config.setting_configuration_id,
                version=config.version,
                query_column=config.query_column,
            )
        elif config.type == "unsaved":
            # Convert request settings to response settings via internal model
            if isinstance(
                config.settings,
                WeaviateHybridSearchSettingsConfigurationRequest,
            ):
                internal = (
                    WeaviateHybridSearchSettingsConfiguration._from_request_model(
                        config.settings,
                    )
                )
                response_settings = internal.to_response_model()
            elif isinstance(
                config.settings,
                WeaviateKeywordSearchSettingsConfigurationRequest,
            ):
                internal = (
                    WeaviateKeywordSearchSettingsConfiguration._from_request_model(
                        config.settings,
                    )
                )
                response_settings = internal.to_response_model()
            elif isinstance(
                config.settings,
                WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
            ):
                internal = WeaviateVectorSimilarityTextSearchSettingsConfiguration._from_request_model(
                    config.settings,
                )
                response_settings = internal.to_response_model()
            else:
                raise ValueError(
                    f"Unknown settings type: {type(config.settings)}",
                )

            return UnsavedRagConfigResponse(
                type="unsaved",
                unsaved_id=config.unsaved_id,
                rag_provider_id=config.rag_provider_id,
                settings=response_settings,
                query_column=config.query_column,
            )
        else:
            raise ValueError(f"Unknown RAG config type: {config.type}")

    def _get_db_experiment(self, experiment_id: str) -> DatabaseRagExperiment:
        """Get database experiment by ID or raise 404"""
        db_experiment = (
            self.db_session.query(DatabaseRagExperiment)
            .options(joinedload(DatabaseRagExperiment.dataset))
            .filter(DatabaseRagExperiment.id == experiment_id)
            .first()
        )
        if not db_experiment:
            raise HTTPException(
                status_code=404,
                detail=f"RAG experiment {experiment_id} not found.",
            )
        return db_experiment

    def _db_experiment_to_summary(
        self,
        db_experiment: DatabaseRagExperiment,
    ) -> RagExperimentSummary:
        """Convert database experiment to summary schema"""
        # Convert JSON RAG configs to Pydantic models (request types)
        # Use TypeAdapter since RagConfig is a type alias, not a BaseModel
        rag_configs_request = [
            RagConfigAdapter.validate_python(config)
            for config in db_experiment.rag_configs
        ]

        # Convert request types to response types
        rag_configs = [
            self._convert_rag_config_to_response(config)
            for config in rag_configs_request
        ]

        # Get dataset name from relationship
        dataset_name = db_experiment.dataset.name

        return RagExperimentSummary(
            id=db_experiment.id,
            name=db_experiment.name,
            description=db_experiment.description,
            created_at=(
                db_experiment.created_at.isoformat()
                if db_experiment.created_at
                else None
            ),
            finished_at=(
                db_experiment.finished_at.isoformat()
                if db_experiment.finished_at
                else None
            ),
            status=db_experiment.status,
            dataset_id=db_experiment.dataset_id,
            dataset_name=dataset_name,
            dataset_version=db_experiment.dataset_version,
            rag_configs=rag_configs,
            total_rows=db_experiment.total_rows,
            completed_rows=db_experiment.completed_rows,
            failed_rows=db_experiment.failed_rows,
            total_cost=db_experiment.total_cost,
        )

    def _db_experiment_to_detail(
        self,
        db_experiment: DatabaseRagExperiment,
    ) -> RagExperimentDetail:
        """Convert database experiment to detail schema"""
        # Convert JSON RAG configs to Pydantic models (request types)
        # Use TypeAdapter since RagConfig is a type alias, not a BaseModel
        rag_configs_request = [
            RagConfigAdapter.validate_python(config)
            for config in db_experiment.rag_configs
        ]

        # Convert request types to response types
        rag_configs = [
            self._convert_rag_config_to_response(config)
            for config in rag_configs_request
        ]

        # Convert JSON eval configs to Pydantic models
        eval_list = [
            EvalRef.model_validate(eval_config)
            for eval_config in db_experiment.eval_configs
        ]

        # Convert summary results to Pydantic model
        summary_results = RagSummaryResults.model_validate(
            db_experiment.summary_results or {"rag_eval_summaries": []},
        )

        # Convert dataset row filter to Pydantic models if present
        dataset_row_filter = None
        if db_experiment.dataset_row_filter:
            dataset_row_filter = [
                NewDatasetVersionRowColumnItemRequest.model_validate(filter_item)
                for filter_item in db_experiment.dataset_row_filter
            ]

        # Get dataset name from relationship
        dataset_name = db_experiment.dataset.name

        return RagExperimentDetail(
            id=db_experiment.id,
            name=db_experiment.name,
            description=db_experiment.description,
            created_at=(
                db_experiment.created_at.isoformat()
                if db_experiment.created_at
                else None
            ),
            finished_at=(
                db_experiment.finished_at.isoformat()
                if db_experiment.finished_at
                else None
            ),
            status=db_experiment.status,
            rag_configs=rag_configs,
            total_rows=db_experiment.total_rows,
            completed_rows=db_experiment.completed_rows,
            failed_rows=db_experiment.failed_rows,
            total_cost=db_experiment.total_cost,
            dataset_ref=DatasetRef(
                id=db_experiment.dataset_id,
                name=dataset_name,
                version=db_experiment.dataset_version,
            ),
            eval_list=eval_list,
            dataset_row_filter=dataset_row_filter,
            summary_results=summary_results,
        )

    def _db_test_case_to_schema(
        self,
        db_test_case: DatabaseRagExperimentTestCase,
    ) -> RagTestCase:
        """Convert database test case to schema"""
        # Convert JSON input variables to Pydantic models
        # Convert RAG results
        rag_results = []
        for rag_result in db_test_case.rag_results:
            # Convert eval scores
            evals = []
            for eval_score in rag_result.eval_scores:
                eval_input_variables = [
                    InputVariable.model_validate(var)
                    for var in eval_score.eval_input_variables
                ]

                # convert eval results - may be None if not yet executed
                eval_result = None
                if eval_score.eval_result_score is not None:
                    eval_result = EvalExecutionResult(
                        score=eval_score.eval_result_score,
                        explanation=eval_score.eval_result_explanation or "",
                        cost=eval_score.eval_result_cost or "0.0",
                    )

                evals.append(
                    EvalExecution(
                        eval_name=eval_score.eval_name,
                        eval_version=str(eval_score.eval_version),
                        eval_input_variables=eval_input_variables,
                        eval_results=eval_result,
                    ),
                )

            # Convert search output - validate against RagProviderQueryResponse schema
            search_output = None
            if rag_result.search_output:
                # Validate the stored dict against the structured response schema
                validated_response = RagProviderQueryResponse.model_validate(
                    rag_result.search_output,
                )
                search_output = RagSearchOutput(response=validated_response)

            rag_results.append(
                RagResult(
                    rag_config_key=rag_result.rag_config_key,
                    rag_config_type=rag_result.rag_config_type,
                    setting_configuration_id=rag_result.setting_configuration_id,
                    setting_configuration_version=rag_result.setting_configuration_version,
                    query_text=rag_result.query_text,
                    output=search_output,
                    evals=evals,
                ),
            )

        return RagTestCase(
            status=db_test_case.status,
            dataset_row_id=db_test_case.dataset_row_id,
            rag_results=rag_results,
            total_cost=db_test_case.total_cost,
        )

    def _validate_experiment_references(
        self,
        task_id: str,
        request: CreateRagExperimentRequest,
    ) -> Tuple[
        List[RagConfig],
        List[Tuple[EvalRef, DatabaseLLMEval]],
        DatabaseDatasetVersion,
    ]:
        """Validate that all referenced resources exist and return validated RAG configs"""
        # Validate task exists
        task = (
            self.db_session.query(DatabaseTask)
            .filter(DatabaseTask.id == task_id)
            .first()
        )
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Validate dataset and version exist
        dataset = (
            self.db_session.query(DatabaseDataset)
            .filter(DatabaseDataset.id == request.dataset_ref.id)
            .first()
        )
        if not dataset:
            raise ValueError(f"Dataset {request.dataset_ref.id} not found")

        dataset_version = (
            self.db_session.query(DatabaseDatasetVersion)
            .filter(
                DatabaseDatasetVersion.dataset_id == request.dataset_ref.id,
                DatabaseDatasetVersion.version_number == request.dataset_ref.version,
            )
            .first()
        )
        if not dataset_version:
            raise ValueError(
                f"Dataset version {request.dataset_ref.version} not found for dataset {request.dataset_ref.id}",
            )

        # Validate and process RAG configs
        validated_rag_configs = []
        unsaved_config_counter = 0

        for config in request.rag_configs:
            if config.type == "saved":
                # Validate RAG setting configuration exists
                setting_config = (
                    self.db_session.query(DatabaseRagSearchSettingConfiguration)
                    .filter(
                        DatabaseRagSearchSettingConfiguration.task_id == task_id,
                        DatabaseRagSearchSettingConfiguration.id
                        == config.setting_configuration_id,
                    )
                    .first()
                )
                if not setting_config:
                    raise ValueError(
                        f"RAG setting configuration '{config.setting_configuration_id}' not found for task {task_id}",
                    )

                # Validate RAG setting configuration version exists
                setting_version = (
                    self.db_session.query(DatabaseRagSearchSettingConfigurationVersion)
                    .filter(
                        DatabaseRagSearchSettingConfigurationVersion.setting_configuration_id
                        == config.setting_configuration_id,
                        DatabaseRagSearchSettingConfigurationVersion.version_number
                        == config.version,
                        DatabaseRagSearchSettingConfigurationVersion.deleted_at.is_(
                            None,
                        ),
                    )
                    .first()
                )
                if not setting_version:
                    raise ValueError(
                        f"RAG setting configuration version {config.version} not found for setting configuration {config.setting_configuration_id}",
                    )

                # Validate that the setting configuration has a provider (rag_provider_id is in the setting config)
                if not setting_config.rag_provider_id:
                    raise ValueError(
                        f"RAG setting configuration '{config.setting_configuration_id}' does not have a provider configured",
                    )

                # Validate RAG provider exists (get it from the setting config)
                rag_provider = (
                    self.db_session.query(DatabaseRagProviderConfiguration)
                    .filter(
                        DatabaseRagProviderConfiguration.task_id == task_id,
                        DatabaseRagProviderConfiguration.id
                        == setting_config.rag_provider_id,
                    )
                    .first()
                )
                if not rag_provider:
                    raise ValueError(
                        f"RAG provider '{setting_config.rag_provider_id}' referenced by setting configuration '{config.setting_configuration_id}' not found for task {task_id}",
                    )

                validated_rag_configs.append(config)

            elif config.type == "unsaved":
                # Validate unsaved RAG configuration
                if not config.settings:
                    raise ValueError("Unsaved RAG config must have settings")

                # Generate UUID for unsaved config (use provided one if exists, otherwise generate new)
                unsaved_id = config.unsaved_id if config.unsaved_id else uuid4()

                # Validate RAG provider exists
                rag_provider = (
                    self.db_session.query(DatabaseRagProviderConfiguration)
                    .filter(
                        DatabaseRagProviderConfiguration.task_id == task_id,
                        DatabaseRagProviderConfiguration.id == config.rag_provider_id,
                    )
                    .first()
                )
                if not rag_provider:
                    raise ValueError(
                        f"RAG provider '{config.rag_provider_id}' not found for task {task_id}",
                    )

                # Create updated config with UUID
                updated_config = UnsavedRagConfig(
                    type="unsaved",
                    unsaved_id=unsaved_id,
                    rag_provider_id=config.rag_provider_id,
                    settings=config.settings,
                    query_column=config.query_column,
                )
                validated_rag_configs.append(updated_config)
            else:
                raise ValueError(f"Unknown RAG config type: {config.type}")

        # Validate eval versions exist
        llm_evals = []
        for eval_ref in request.eval_list:
            llm_eval = (
                self.db_session.query(DatabaseLLMEval)
                .filter(
                    DatabaseLLMEval.task_id == task_id,
                    DatabaseLLMEval.name == eval_ref.name,
                    DatabaseLLMEval.version == eval_ref.version,
                )
                .first()
            )
            if not llm_eval:
                raise ValueError(
                    f"Eval '{eval_ref.name}' version {eval_ref.version} not found for task {task_id}",
                )
            llm_evals.append((eval_ref, llm_eval))

        # Validate that all dataset column references exist in the dataset version
        dataset_columns = set(dataset_version.column_names)

        # Validate dataset row filter columns if provided
        if request.dataset_row_filter:
            for filter_item in request.dataset_row_filter:
                if filter_item.column_name not in dataset_columns:
                    raise ValueError(
                        f"Dataset column '{filter_item.column_name}' referenced in dataset_row_filter not found in dataset version. "
                        f"Available columns: {', '.join(sorted(dataset_columns))}",
                    )

        # Validate query_column for each RAG config
        for config in validated_rag_configs:
            query_column_name = config.query_column.dataset_column.name
            if query_column_name not in dataset_columns:
                if config.type == "saved":
                    raise ValueError(
                        f"Dataset column '{query_column_name}' referenced in RAG config (setting {config.setting_configuration_id}, version {config.version}) not found in dataset version. "
                        f"Available columns: {', '.join(sorted(dataset_columns))}",
                    )
                else:
                    raise ValueError(
                        f"Dataset column '{query_column_name}' referenced in unsaved RAG config '{config.unsaved_id}' not found in dataset version. "
                        f"Available columns: {', '.join(sorted(dataset_columns))}",
                    )

        # Check eval variable mappings - validate dataset columns exist and no duplicates
        for eval_ref in request.eval_list:
            eval_variable_names = []
            for mapping in eval_ref.variable_mapping:
                eval_variable_names.append(mapping.variable_name)
                if mapping.source.type == "dataset_column":
                    column_name = mapping.source.dataset_column.name
                    if column_name not in dataset_columns:
                        raise ValueError(
                            f"Dataset column '{column_name}' referenced in eval '{eval_ref.name}' variable mapping not found in dataset version. "
                            f"Available columns: {', '.join(sorted(dataset_columns))}",
                        )

            # Check for duplicate eval variable mappings
            duplicate_eval_vars = [
                var
                for var in set(eval_variable_names)
                if eval_variable_names.count(var) > 1
            ]
            if duplicate_eval_vars:
                raise ValueError(
                    f"Duplicate variable mappings found in eval '{eval_ref.name}' configuration: {', '.join(sorted(duplicate_eval_vars))}. "
                    f"Each variable must be mapped exactly once.",
                )

        # Validate that all eval variables are provided in the configuration
        for eval_ref, llm_eval in llm_evals:
            provided_eval_variables = {
                mapping.variable_name for mapping in eval_ref.variable_mapping
            }
            required_variables = set(llm_eval.variables)
            missing_variables = required_variables - provided_eval_variables

            if missing_variables:
                raise ValueError(
                    f"Eval '{eval_ref.name}' version {eval_ref.version} requires variables {sorted(missing_variables)} "
                    f"but they are not provided in the variable mapping. "
                    f"Provided variables: {sorted(provided_eval_variables)}",
                )

        return validated_rag_configs, llm_evals, dataset_version

    def _create_test_cases_for_dataset(
        self,
        experiment_id: str,
        dataset_ref: DatasetRefInput,
        rag_configs: List[RagConfig],
        eval_configs: List[Tuple[EvalRef, DatabaseLLMEval]],
        dataset_row_filter: Optional[
            List[NewDatasetVersionRowColumnItemRequest]
        ] = None,
    ) -> int:
        """Create test cases for each row in the dataset version, including RAG results and eval scores"""
        # Get all rows for this dataset version
        dataset_rows = (
            self.db_session.query(DatabaseDatasetVersionRow)
            .filter(
                DatabaseDatasetVersionRow.dataset_id == dataset_ref.id,
                DatabaseDatasetVersionRow.version_number == dataset_ref.version,
            )
            .all()
        )

        # Helper function to check if a row matches all filter conditions (AND logic)
        def _row_matches_filter(db_row: DatabaseDatasetVersionRow) -> bool:
            if not dataset_row_filter:
                return True  # No filter means all rows match

            # Row must match ALL filter conditions to be included
            for filter_condition in dataset_row_filter:
                row_value = db_row.data.get(filter_condition.column_name)
                # Convert both to strings for comparison since row data can be any JSON type
                # (int, bool, etc.) but filter values are always strings per the schema
                if str(row_value) != str(filter_condition.column_value):
                    return False
            return True

        # Filter rows based on dataset_row_filter if provided
        filtered_rows = [row for row in dataset_rows if _row_matches_filter(row)]

        # Create a test case for each filtered row
        for row in filtered_rows:
            row_data = row.data  # This is the JSON data for the row

            # Create the test case
            test_case = DatabaseRagExperimentTestCase(
                id=str(uuid4()),
                experiment_id=experiment_id,
                dataset_row_id=str(row.id),
                status=TestCaseStatus.QUEUED,
            )
            self.db_session.add(test_case)

            # Create RAG results for each RAG config in this test case
            for config in rag_configs:
                if config.type == "saved":
                    # Create RAG config key: "saved:setting_config_id:version"
                    rag_config_key = (
                        f"saved:{config.setting_configuration_id}:{config.version}"
                    )
                    rag_config_type = "saved"
                    setting_configuration_id = config.setting_configuration_id
                    setting_configuration_version = config.version
                else:  # unsaved
                    # Create RAG config key: "unsaved:uuid"
                    rag_config_key = f"unsaved:{config.unsaved_id}"
                    rag_config_type = "unsaved"
                    setting_configuration_id = None
                    setting_configuration_version = None

                # Create result for RAG config
                rag_result = DatabaseRagExperimentTestCaseRagResult(
                    id=str(uuid4()),
                    test_case_id=test_case.id,
                    rag_config_key=rag_config_key,
                    rag_config_type=rag_config_type,
                    setting_configuration_id=setting_configuration_id,
                    setting_configuration_version=setting_configuration_version,
                    query_text="...waiting to run...",  # Will be filled when experiment runs
                    search_output={},  # Will be filled when experiment runs
                )
                self.db_session.add(rag_result)

                # Create eval score entries for each eval configuration
                for eval_ref, llm_eval in eval_configs:
                    # Build eval input variables based on the mapping
                    eval_input_variables = []
                    for mapping in eval_ref.variable_mapping:
                        variable_name = mapping.variable_name

                        # Check the source type
                        if mapping.source.type == "dataset_column":
                            # Get value from dataset row
                            column_name = mapping.source.dataset_column.name
                            column_value = row_data.get(column_name)
                            eval_input_variables.append(
                                {
                                    "variable_name": variable_name,
                                    "value": (
                                        str(column_value)
                                        if column_value is not None
                                        else ""
                                    ),
                                },
                            )
                        elif mapping.source.type == "experiment_output":
                            # Mark as placeholder - will be filled from RAG search output when experiment runs
                            eval_input_variables.append(
                                {
                                    "variable_name": variable_name,
                                    "value": "...waiting for response...",  # Will be filled when experiment runs
                                },
                            )

                    eval_score = DatabaseRagExperimentTestCaseRagResultEvalScore(
                        id=str(uuid4()),
                        rag_result_id=rag_result.id,
                        eval_name=llm_eval.name,
                        eval_version=llm_eval.version,
                        eval_input_variables=eval_input_variables,
                        eval_result_score=None,  # Will be filled when experiment runs
                        eval_result_explanation=None,
                        eval_result_cost=None,
                    )
                    self.db_session.add(eval_score)

        return len(filtered_rows)

    def create_experiment(
        self,
        task_id: str,
        experiment_id: str,
        request: CreateRagExperimentRequest,
    ) -> RagExperimentSummary:
        """Create a new RAG experiment with test cases"""
        # Validate all references
        validated_rag_configs, llm_evals, dataset_version = (
            self._validate_experiment_references(task_id, request)
        )

        # Convert validated configs to JSON-serializable format
        # can't use python mode because then types that are not JSON-serializable (eg. UUID) are included
        rag_configs_json = [
            config.model_dump(mode="json") for config in validated_rag_configs
        ]

        # Convert eval configs to JSON-serializable format
        eval_configs_json = [
            eval_ref.model_dump(mode="python") for eval_ref, _ in llm_evals
        ]

        # Convert dataset row filter to JSON-serializable format if present
        dataset_row_filter_json = None
        if request.dataset_row_filter:
            dataset_row_filter_json = [
                filter_item.model_dump(mode="python")
                for filter_item in request.dataset_row_filter
            ]

        # Create the experiment
        db_experiment = DatabaseRagExperiment(
            id=experiment_id,
            task_id=task_id,
            name=request.name,
            description=request.description,
            status=ExperimentStatus.QUEUED,
            rag_configs=rag_configs_json,
            dataset_id=request.dataset_ref.id,
            dataset_version=request.dataset_ref.version,
            dataset_row_filter=dataset_row_filter_json,
            eval_configs=eval_configs_json,
            total_rows=0,  # Will be updated after creating test cases
            completed_rows=0,
            failed_rows=0,
        )
        self.db_session.add(db_experiment)

        # Create test cases
        total_rows = self._create_test_cases_for_dataset(
            experiment_id=experiment_id,
            dataset_ref=request.dataset_ref,
            rag_configs=validated_rag_configs,
            eval_configs=llm_evals,
            dataset_row_filter=request.dataset_row_filter,
        )

        # Update total rows
        db_experiment.total_rows = total_rows
        self.db_session.commit()
        self.db_session.refresh(db_experiment)

        return self._db_experiment_to_summary(db_experiment)

    def get_experiment(self, experiment_id: str) -> RagExperimentDetail:
        """Get a RAG experiment by ID"""
        db_experiment = self._get_db_experiment(experiment_id)
        return self._db_experiment_to_detail(db_experiment)

    def list_experiments(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters,
        search: Optional[str] = None,
        dataset_id: Optional[UUID] = None,
    ) -> Tuple[List[RagExperimentSummary], int]:
        """List RAG experiments for a task with optional filtering and pagination"""
        query = self.db_session.query(DatabaseRagExperiment).filter(
            DatabaseRagExperiment.task_id == task_id,
        )

        # Apply search filter if provided
        if search:
            search_filter = or_(
                DatabaseRagExperiment.name.ilike(f"%{search}%"),
                DatabaseRagExperiment.description.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # Apply dataset filter if provided
        if dataset_id:
            query = query.filter(DatabaseRagExperiment.dataset_id == dataset_id)

        # Apply sorting
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseRagExperiment.created_at))
        elif pagination_parameters.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseRagExperiment.created_at))

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        db_experiments = (
            query.options(joinedload(DatabaseRagExperiment.dataset))
            .offset(offset)
            .limit(pagination_parameters.page_size)
            .all()
        )

        # Convert to summary schemas
        summaries = [
            self._db_experiment_to_summary(db_exp) for db_exp in db_experiments
        ]

        return summaries, total_count

    def _get_db_test_cases(
        self,
        experiment_id: str,
        status_filter: Optional[TestCaseStatus] = None,
    ) -> List[DatabaseRagExperimentTestCase]:
        query = self.db_session.query(DatabaseRagExperimentTestCase).filter(
            DatabaseRagExperimentTestCase.experiment_id == experiment_id,
        )
        if status_filter:
            query = query.filter(DatabaseRagExperimentTestCase.status == status_filter)
        return query.all()

    def _get_db_test_case(
        self,
        test_case_id: str,
    ) -> Optional[DatabaseRagExperimentTestCase]:
        test_case = (
            self.db_session.query(DatabaseRagExperimentTestCase)
            .filter_by(id=test_case_id)
            .first()
        )
        return test_case

    def get_test_cases(
        self,
        experiment_id: str,
        pagination_parameters: PaginationParameters,
    ) -> Tuple[List[RagTestCase], int]:
        """Get test cases for a RAG experiment with pagination"""
        # Verify experiment exists
        self._get_db_experiment(experiment_id)

        # Query test cases
        query = self.db_session.query(DatabaseRagExperimentTestCase).filter(
            DatabaseRagExperimentTestCase.experiment_id == experiment_id,
        )

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        db_test_cases = (
            query.options(
                joinedload(DatabaseRagExperimentTestCase.rag_results).joinedload(
                    DatabaseRagExperimentTestCaseRagResult.eval_scores,
                ),
            )
            .offset(offset)
            .limit(pagination_parameters.page_size)
            .all()
        )

        # Convert to schemas
        test_cases = [
            self._db_test_case_to_schema(db_test_case) for db_test_case in db_test_cases
        ]

        return test_cases, total_count

    def get_rag_config_results(
        self,
        experiment_id: str,
        rag_config_key: str,
        pagination_parameters: PaginationParameters,
    ) -> Tuple[List[RagConfigResult], int]:
        """Get results for a specific RAG configuration within an experiment"""
        # Verify experiment exists first
        db_experiment = self._get_db_experiment(experiment_id)

        # Verify the rag_config_key exists in this experiment's rag_configs
        rag_config_keys_in_experiment = []
        for config in db_experiment.rag_configs:
            if config.get("type") == "saved":
                rag_config_keys_in_experiment.append(
                    f"saved:{config['setting_configuration_id']}:{config['version']}",
                )
            elif config.get("type") == "unsaved":
                rag_config_keys_in_experiment.append(
                    f"unsaved:{config['unsaved_id']}",
                )

        if rag_config_key not in rag_config_keys_in_experiment:
            raise HTTPException(
                status_code=404,
                detail=f"RAG config key '{rag_config_key}' not found in experiment {experiment_id}. "
                f"Available RAG config keys: {', '.join(rag_config_keys_in_experiment)}",
            )

        # Query test cases with matching RAG results
        base_query = (
            self.db_session.query(DatabaseRagExperimentTestCase)
            .filter(DatabaseRagExperimentTestCase.experiment_id == experiment_id)
            .join(DatabaseRagExperimentTestCaseRagResult)
            .filter(
                DatabaseRagExperimentTestCaseRagResult.rag_config_key == rag_config_key,
            )
        )

        # Apply sorting - sort by test case created_at field
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            base_query = base_query.order_by(
                desc(DatabaseRagExperimentTestCase.created_at),
            )
        else:
            base_query = base_query.order_by(
                asc(DatabaseRagExperimentTestCase.created_at),
            )

        # Get total count
        total_count = base_query.count()

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        db_test_cases = (
            base_query.options(
                joinedload(DatabaseRagExperimentTestCase.rag_results).joinedload(
                    DatabaseRagExperimentTestCaseRagResult.eval_scores,
                ),
            )
            .offset(offset)
            .limit(pagination_parameters.page_size)
            .all()
        )

        # Convert to schemas - extract the specific RAG result for each test case
        config_results = []
        for db_test_case in db_test_cases:
            # Find the matching RAG result
            matching_rag_result = None
            for rag_result in db_test_case.rag_results:
                if rag_result.rag_config_key == rag_config_key:
                    matching_rag_result = rag_result
                    break

            if not matching_rag_result:
                continue

            # Convert eval scores
            evals = []
            for eval_score in matching_rag_result.eval_scores:
                eval_input_variables = [
                    InputVariable.model_validate(var)
                    for var in eval_score.eval_input_variables
                ]

                eval_result = None
                if eval_score.eval_result_score is not None:
                    eval_result = EvalExecutionResult(
                        score=eval_score.eval_result_score,
                        explanation=eval_score.eval_result_explanation or "",
                        cost=eval_score.eval_result_cost or "0.0",
                    )

                evals.append(
                    EvalExecution(
                        eval_name=eval_score.eval_name,
                        eval_version=str(eval_score.eval_version),
                        eval_input_variables=eval_input_variables,
                        eval_results=eval_result,
                    ),
                )

            # Convert search output - validate against RagProviderQueryResponse schema
            search_output = None
            if matching_rag_result.search_output:
                # Validate the stored dict against the structured response schema
                validated_response = RagProviderQueryResponse.model_validate(
                    matching_rag_result.search_output,
                )
                search_output = RagSearchOutput(response=validated_response)

            # Calculate total cost from eval costs (RAG searches don't have cost)
            total_cost = None
            eval_costs = [
                float(eval_score.eval_result_cost)
                for eval_score in matching_rag_result.eval_scores
                if eval_score.eval_result_cost
            ]
            if eval_costs:
                total_cost = str(sum(eval_costs))

            config_results.append(
                RagConfigResult(
                    status=db_test_case.status,
                    dataset_row_id=db_test_case.dataset_row_id,
                    query_text=matching_rag_result.query_text,
                    output=search_output,
                    evals=evals,
                    total_cost=total_cost,
                ),
            )

        return config_results, total_count
