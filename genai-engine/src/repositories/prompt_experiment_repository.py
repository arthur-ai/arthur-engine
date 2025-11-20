import logging
from typing import List, Optional, Tuple
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from db_models.dataset_models import (
    DatabaseDataset,
    DatabaseDatasetVersion,
    DatabaseDatasetVersionRow,
)
from db_models.llm_eval_models import DatabaseLLMEval
from db_models.prompt_experiment_models import (
    DatabasePromptExperiment,
    DatabasePromptExperimentTestCase,
    DatabasePromptExperimentTestCasePromptResult,
    DatabasePromptExperimentTestCasePromptResultEvalScore,
)
from db_models.task_models import DatabaseTask
from schemas.prompt_experiment_schemas import (
    CreatePromptExperimentRequest,
    DatasetRef,
    EvalExecution,
    EvalExecutionResult,
    EvalRef,
    ExperimentStatus,
    InputVariable,
    PromptConfig,
    PromptExperimentDetail,
    PromptExperimentSummary,
    PromptOutput,
    PromptResult,
    PromptVariableMapping,
    PromptVersionResult,
    SavedPromptConfig,
    SummaryResults,
    TestCase,
    TestCaseStatus,
    UnsavedPromptConfig,
)
from services.prompt.chat_completion_service import ChatCompletionService

logger = logging.getLogger(__name__)


class PromptExperimentRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.chat_completion_service = ChatCompletionService()

    def _get_db_experiment(self, experiment_id: str) -> DatabasePromptExperiment:
        """Get database experiment by ID or raise 404"""
        db_experiment = (
            self.db_session.query(DatabasePromptExperiment)
            .filter(DatabasePromptExperiment.id == experiment_id)
            .first()
        )
        if not db_experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment {experiment_id} not found.",
            )
        return db_experiment

    def _db_experiment_to_summary(
        self,
        db_experiment: DatabasePromptExperiment,
    ) -> PromptExperimentSummary:
        """Convert database experiment to summary schema"""
        # Convert JSON prompt configs to Pydantic models
        prompt_configs = [
            (
                SavedPromptConfig.model_validate(config)
                if config.get("type") == "saved"
                else UnsavedPromptConfig.model_validate(config)
            )
            for config in db_experiment.prompt_configs
        ]

        return PromptExperimentSummary(
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
            prompt_configs=prompt_configs,
            total_rows=db_experiment.total_rows,
            completed_rows=db_experiment.completed_rows,
            failed_rows=db_experiment.failed_rows,
            total_cost=db_experiment.total_cost,
        )

    def _db_experiment_to_detail(
        self,
        db_experiment: DatabasePromptExperiment,
    ) -> PromptExperimentDetail:
        """Convert database experiment to detail schema"""
        # Convert JSON prompt configs to Pydantic models
        prompt_configs = [
            (
                SavedPromptConfig.model_validate(config)
                if config.get("type") == "saved"
                else UnsavedPromptConfig.model_validate(config)
            )
            for config in db_experiment.prompt_configs
        ]

        # Convert JSON prompt variable mappings to Pydantic models
        prompt_variable_mappings = [
            PromptVariableMapping.model_validate(mapping)
            for mapping in db_experiment.prompt_variable_mapping
        ]

        # Convert JSON eval configs to Pydantic models
        eval_list = [
            EvalRef.model_validate(eval_config)
            for eval_config in db_experiment.eval_configs
        ]

        # Convert summary results to Pydantic model
        summary_results = SummaryResults.model_validate(
            db_experiment.summary_results or {"prompt_eval_summaries": []},
        )

        return PromptExperimentDetail(
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
            prompt_configs=prompt_configs,
            total_rows=db_experiment.total_rows,
            completed_rows=db_experiment.completed_rows,
            failed_rows=db_experiment.failed_rows,
            total_cost=db_experiment.total_cost,
            dataset_ref=DatasetRef(
                id=db_experiment.dataset_id,
                version=db_experiment.dataset_version,
            ),
            prompt_variable_mapping=prompt_variable_mappings,
            eval_list=eval_list,
            summary_results=summary_results,
        )

    def _db_test_case_to_schema(
        self,
        db_test_case: DatabasePromptExperimentTestCase,
    ) -> TestCase:
        """Convert database test case to schema"""
        # Convert JSON input variables to Pydantic models
        input_variables = [
            InputVariable.model_validate(var)
            for var in db_test_case.prompt_input_variables
        ]

        # Convert nested prompt results from database models to Pydantic models
        prompt_results = []
        for db_prompt_result in db_test_case.prompt_results:
            # Convert eval scores for this prompt result
            eval_executions = []
            for db_eval_score in db_prompt_result.eval_scores:
                eval_input_variables = [
                    InputVariable.model_validate(var)
                    for var in db_eval_score.eval_input_variables
                ]

                # Convert eval results - may be None if not yet executed
                eval_results = None
                if db_eval_score.eval_result_score is not None:
                    eval_results = EvalExecutionResult(
                        score=db_eval_score.eval_result_score,
                        explanation=db_eval_score.eval_result_explanation or "",
                        cost=db_eval_score.eval_result_cost or "0",
                    )

                eval_execution = EvalExecution(
                    eval_name=db_eval_score.eval_name,
                    eval_version=str(db_eval_score.eval_version),
                    eval_input_variables=eval_input_variables,
                    eval_results=eval_results,
                )
                eval_executions.append(eval_execution)

            # Convert prompt output - may be None if not yet executed
            # Include output if we have any of: content, tool_calls, or cost
            prompt_output = None
            if (
                db_prompt_result.output_content is not None
                or db_prompt_result.output_tool_calls is not None
                or db_prompt_result.output_cost is not None
            ):
                prompt_output = PromptOutput(
                    content=db_prompt_result.output_content or "",
                    tool_calls=db_prompt_result.output_tool_calls or [],
                    cost=db_prompt_result.output_cost or "0",
                )

            # Build the full prompt result
            prompt_result = PromptResult(
                prompt_key=db_prompt_result.prompt_key,
                prompt_type=db_prompt_result.prompt_type,
                name=db_prompt_result.name,
                version=(
                    str(db_prompt_result.version)
                    if db_prompt_result.version is not None
                    else None
                ),
                rendered_prompt=db_prompt_result.rendered_prompt,
                output=prompt_output,
                evals=eval_executions,
            )
            prompt_results.append(prompt_result)

        return TestCase(
            status=db_test_case.status,
            dataset_row_id=db_test_case.dataset_row_id,
            prompt_input_variables=input_variables,
            prompt_results=prompt_results,
            total_cost=db_test_case.total_cost,
        )

    def _validate_experiment_references(
        self,
        task_id: str,
        request: CreatePromptExperimentRequest,
    ) -> Tuple[
        List[PromptConfig],
        List[Tuple[EvalRef, DatabaseLLMEval]],
        DatabaseDatasetVersion,
    ]:
        """Validate that all referenced resources exist and return validated prompt configs with auto-names"""
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

        # Validate and process prompt configs (saved and unsaved)
        validated_prompt_configs = []
        unsaved_prompt_counter = 1
        all_prompt_variables = set()

        for config in request.prompt_configs:
            if isinstance(config, SavedPromptConfig):
                # Validate saved prompt exists in database
                prompt = (
                    self.db_session.query(DatabaseAgenticPrompt)
                    .filter(
                        DatabaseAgenticPrompt.task_id == task_id,
                        DatabaseAgenticPrompt.name == config.name,
                        DatabaseAgenticPrompt.version == config.version,
                    )
                    .first()
                )
                if not prompt:
                    raise ValueError(
                        f"Prompt '{config.name}' version {config.version} not found for task {task_id}",
                    )
                # Collect variables from this saved prompt
                all_prompt_variables.update(prompt.variables)
                validated_prompt_configs.append(config)

            elif isinstance(config, UnsavedPromptConfig):
                # Validate unsaved prompt configuration
                if not config.messages or len(config.messages) == 0:
                    raise ValueError("Unsaved prompt must have non-empty messages")

                # Auto-generate name if not provided
                auto_name = f"unsaved_prompt_{unsaved_prompt_counter}"
                unsaved_prompt_counter += 1

                # Auto-detect variables if not provided
                if config.variables is None:
                    try:
                        missing_vars = self.chat_completion_service.find_missing_variables_in_messages(
                            config.messages,
                            {},
                        )
                        detected_variables = list(missing_vars)
                    except Exception as e:
                        logger.warning(
                            f"Failed to auto-detect variables for unsaved prompt: {e}",
                        )
                        detected_variables = []
                else:
                    detected_variables = config.variables

                # Collect variables from this unsaved prompt
                all_prompt_variables.update(detected_variables)

                # Create updated config with auto-name and variables
                updated_config = UnsavedPromptConfig(
                    type="unsaved",
                    auto_name=auto_name,
                    messages=config.messages,
                    model_name=config.model_name,
                    model_provider=config.model_provider,
                    tools=config.tools,
                    config=config.config,
                    variables=detected_variables,
                )
                validated_prompt_configs.append(updated_config)

        # Validate eval versions exist and collect their variables
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

        # Check shared prompt variable mappings - validate dataset columns exist and no duplicates
        # (Type enforcement is handled by schema - PromptVariableMapping only accepts DatasetColumnVariableSource)
        prompt_variable_names = []
        for mapping in request.prompt_variable_mapping:
            column_name = mapping.source.dataset_column.name
            if column_name not in dataset_columns:
                raise ValueError(
                    f"Dataset column '{column_name}' referenced in prompt variable mapping not found in dataset version. "
                    f"Available columns: {', '.join(sorted(dataset_columns))}",
                )
            prompt_variable_names.append(mapping.variable_name)

        # Check for duplicate prompt variable mappings
        duplicate_prompt_vars = [
            var
            for var in set(prompt_variable_names)
            if prompt_variable_names.count(var) > 1
        ]
        if duplicate_prompt_vars:
            raise ValueError(
                f"Duplicate variable mappings found in prompt configuration: {', '.join(sorted(duplicate_prompt_vars))}. "
                f"Each variable must be mapped exactly once.",
            )

        # Validate that all prompt variables across all prompts are provided in the shared mapping
        provided_prompt_variables = set(prompt_variable_names)
        missing_variables = all_prompt_variables - provided_prompt_variables

        if missing_variables:
            raise ValueError(
                f"Prompts require variables {sorted(missing_variables)} "
                f"but they are not provided in the variable mapping. "
                f"Provided variables: {sorted(provided_prompt_variables)}",
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

        return validated_prompt_configs, llm_evals, dataset_version

    def _create_test_cases_for_dataset(
        self,
        experiment_id: str,
        dataset_ref: DatasetRef,
        prompt_variable_mappings: list[PromptVariableMapping],
        prompt_configs: List[PromptConfig],
        eval_configs: List[Tuple[EvalRef, DatabaseLLMEval]],
    ) -> int:
        """Create test cases for each row in the dataset version, including prompt results and eval scores"""
        # Get all rows for this dataset version
        dataset_rows = (
            self.db_session.query(DatabaseDatasetVersionRow)
            .filter(
                DatabaseDatasetVersionRow.dataset_id == dataset_ref.id,
                DatabaseDatasetVersionRow.version_number == dataset_ref.version,
            )
            .all()
        )

        # Create a test case for each row
        for row in dataset_rows:
            # Build prompt input variables from the dataset row data
            prompt_input_variables = []
            row_data = row.data  # This is the JSON data for the row

            for mapping in prompt_variable_mappings:
                variable_name = mapping.variable_name
                column_name = mapping.source.dataset_column.name

                # Get the value from the dataset row
                column_value = row_data.get(column_name)

                prompt_input_variables.append(
                    {
                        "variable_name": variable_name,
                        "value": column_value,
                    },
                )

            # Create the test case
            test_case = DatabasePromptExperimentTestCase(
                id=str(uuid4()),
                experiment_id=experiment_id,
                dataset_row_id=str(row.id),
                status=TestCaseStatus.QUEUED,
                prompt_input_variables=prompt_input_variables,
            )
            self.db_session.add(test_case)

            # Create prompt results for each prompt config in this test case
            for config in prompt_configs:
                if isinstance(config, SavedPromptConfig):
                    # Create result for saved prompt
                    prompt_result = DatabasePromptExperimentTestCasePromptResult(
                        id=str(uuid4()),
                        test_case_id=test_case.id,
                        prompt_key=f"saved:{config.name}:{config.version}",
                        prompt_type="saved",
                        name=config.name,
                        version=config.version,
                        unsaved_prompt_auto_name=None,
                        rendered_prompt="...waiting to run...",  # Will be filled when experiment runs
                        output_content=None,  # Will be filled when experiment runs
                        output_tool_calls=None,
                        output_cost=None,
                    )
                else:  # UnsavedPromptConfig
                    # Create result for unsaved prompt
                    prompt_result = DatabasePromptExperimentTestCasePromptResult(
                        id=str(uuid4()),
                        test_case_id=test_case.id,
                        prompt_key=f"unsaved:{config.auto_name}",
                        prompt_type="unsaved",
                        name=None,
                        version=None,
                        unsaved_prompt_auto_name=config.auto_name,
                        rendered_prompt="...waiting to run...",  # Will be filled when experiment runs
                        output_content=None,  # Will be filled when experiment runs
                        output_tool_calls=None,
                        output_cost=None,
                    )
                self.db_session.add(prompt_result)

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
                                    "value": column_value,
                                },
                            )
                        elif mapping.source.type == "experiment_output":
                            # Mark as placeholder - will be filled from prompt output when experiment runs
                            eval_input_variables.append(
                                {
                                    "variable_name": variable_name,
                                    "value": "...waiting for response...",  # Will be filled when experiment runs
                                },
                            )

                    eval_score = DatabasePromptExperimentTestCasePromptResultEvalScore(
                        id=str(uuid4()),
                        prompt_result_id=prompt_result.id,
                        eval_name=llm_eval.name,
                        eval_version=llm_eval.version,
                        eval_input_variables=eval_input_variables,
                        eval_result_score=None,  # Will be filled when experiment runs
                        eval_result_explanation=None,
                        eval_result_cost=None,
                    )
                    self.db_session.add(eval_score)

        # Commit all the created objects
        self.db_session.flush()

        return len(dataset_rows)

    def create_experiment(
        self,
        task_id: str,
        experiment_id: str,
        request: CreatePromptExperimentRequest,
    ) -> PromptExperimentSummary:
        """Create a new experiment"""
        # Validate all references exist and get validated prompt configs with auto-names
        validated_prompt_configs, eval_configs, dataset_version = (
            self._validate_experiment_references(task_id, request)
        )

        # Create the experiment
        db_experiment = DatabasePromptExperiment(
            id=experiment_id,
            task_id=task_id,
            name=request.name,
            description=request.description,
            status=ExperimentStatus.QUEUED,
            prompt_configs=[config.model_dump() for config in validated_prompt_configs],
            dataset_id=str(request.dataset_ref.id),
            dataset_version=request.dataset_ref.version,
            prompt_variable_mapping=[
                mapping.model_dump() for mapping in request.prompt_variable_mapping
            ],
            eval_configs=[eval_ref.model_dump() for eval_ref in request.eval_list],
            total_rows=0,  # Will be updated after creating test cases
            completed_rows=0,
            failed_rows=0,
        )

        self.db_session.add(db_experiment)

        # Create test cases for each dataset row with prompt input variables, prompt results, and eval scores
        total_rows = self._create_test_cases_for_dataset(
            experiment_id,
            request.dataset_ref,
            request.prompt_variable_mapping,
            validated_prompt_configs,
            eval_configs,
        )

        # Update experiment with total row count
        db_experiment.total_rows = total_rows
        self.db_session.commit()
        self.db_session.refresh(db_experiment)

        return self._db_experiment_to_summary(db_experiment)

    def get_experiment(self, experiment_id: str) -> PromptExperimentDetail:
        """Get experiment by ID"""
        db_experiment = self._get_db_experiment(experiment_id)
        return self._db_experiment_to_detail(db_experiment)

    def list_experiments(
        self,
        task_id: str,
        pagination_params: PaginationParameters,
        status_filter: Optional[str] = None,
        search_text: Optional[str] = None,
    ) -> Tuple[List[PromptExperimentSummary], int]:
        """List experiments for a task with optional filtering"""
        base_query = self.db_session.query(DatabasePromptExperiment).filter(
            DatabasePromptExperiment.task_id == task_id,
        )

        # Apply status filter if provided
        if status_filter:
            base_query = base_query.filter(
                DatabasePromptExperiment.status == status_filter,
            )

        # Apply search filter if provided
        if search_text:
            # Join with dataset table to search dataset name
            base_query = base_query.outerjoin(
                DatabaseDataset,
                DatabasePromptExperiment.dataset_id == DatabaseDataset.id,
            )

            # Search across experiment name, description, prompt name, and dataset name
            search_pattern = f"%{search_text}%"
            base_query = base_query.filter(
                or_(
                    DatabasePromptExperiment.name.ilike(search_pattern),
                    DatabasePromptExperiment.description.ilike(search_pattern),
                    DatabasePromptExperiment.prompt_name.ilike(search_pattern),
                    DatabaseDataset.name.ilike(search_pattern),
                ),
            )

        # Apply sorting - sort by created_at field
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            base_query = base_query.order_by(desc(DatabasePromptExperiment.created_at))
        else:  # ASCENDING or default
            base_query = base_query.order_by(asc(DatabasePromptExperiment.created_at))

        # Calculate total count before pagination
        count = base_query.count()

        # Apply pagination
        base_query = base_query.offset(
            pagination_params.page * pagination_params.page_size,
        )
        db_experiments = base_query.limit(pagination_params.page_size).all()

        return [
            self._db_experiment_to_summary(db_exp) for db_exp in db_experiments
        ], count

    def delete_experiment(self, experiment_id: str) -> None:
        """Delete an experiment and its test cases (cascaded)"""
        db_experiment = self._get_db_experiment(experiment_id)
        self.db_session.delete(db_experiment)
        self.db_session.commit()

    def get_test_cases(
        self,
        experiment_id: str,
        pagination_params: PaginationParameters,
    ) -> Tuple[List[TestCase], int]:
        """Get paginated test cases for an experiment"""
        # Verify experiment exists first
        self._get_db_experiment(experiment_id)

        base_query = self.db_session.query(DatabasePromptExperimentTestCase).filter(
            DatabasePromptExperimentTestCase.experiment_id == experiment_id,
        )

        # Apply sorting - sort by created_at field
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            base_query = base_query.order_by(
                desc(DatabasePromptExperimentTestCase.created_at),
            )
        else:
            base_query = base_query.order_by(
                asc(DatabasePromptExperimentTestCase.created_at),
            )

        # Calculate total count
        count = base_query.count()

        # Apply pagination
        base_query = base_query.offset(
            pagination_params.page * pagination_params.page_size,
        )
        db_test_cases = base_query.limit(pagination_params.page_size).all()

        return [self._db_test_case_to_schema(db_tc) for db_tc in db_test_cases], count

    def get_prompt_version_results(
        self,
        experiment_id: str,
        prompt_key: str,
        pagination_params: PaginationParameters,
    ) -> Tuple[List[PromptVersionResult], int]:
        """Get paginated results for a specific prompt key within an experiment"""
        # Verify experiment exists first
        db_experiment = self._get_db_experiment(experiment_id)

        # Verify the prompt_key exists in this experiment's prompt_configs
        prompt_keys_in_experiment = []
        for config in db_experiment.prompt_configs:
            if config.get("type") == "saved":
                prompt_keys_in_experiment.append(
                    f"saved:{config['name']}:{config['version']}",
                )
            elif config.get("type") == "unsaved":
                prompt_keys_in_experiment.append(f"unsaved:{config['auto_name']}")

        if prompt_key not in prompt_keys_in_experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt key '{prompt_key}' not found in experiment {experiment_id}. "
                f"Available prompt keys: {', '.join(prompt_keys_in_experiment)}",
            )

        # Query test cases with their prompt results filtered for the specific prompt key
        base_query = (
            self.db_session.query(DatabasePromptExperimentTestCase)
            .filter(DatabasePromptExperimentTestCase.experiment_id == experiment_id)
            .join(
                DatabasePromptExperimentTestCasePromptResult,
                DatabasePromptExperimentTestCase.id
                == DatabasePromptExperimentTestCasePromptResult.test_case_id,
            )
            .filter(
                DatabasePromptExperimentTestCasePromptResult.prompt_key == prompt_key,
            )
        )

        # Apply sorting - sort by test case created_at field
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            base_query = base_query.order_by(
                desc(DatabasePromptExperimentTestCase.created_at),
            )
        else:
            base_query = base_query.order_by(
                asc(DatabasePromptExperimentTestCase.created_at),
            )

        # Calculate total count
        count = base_query.count()

        # Apply pagination
        base_query = base_query.offset(
            pagination_params.page * pagination_params.page_size,
        )
        db_test_cases = base_query.limit(pagination_params.page_size).all()

        # Convert each test case to a PromptVersionResult
        results = []
        for db_test_case in db_test_cases:
            # Find the specific prompt result for this prompt key
            db_prompt_result = next(
                (
                    pr
                    for pr in db_test_case.prompt_results
                    if pr.prompt_key == prompt_key
                ),
                None,
            )

            if not db_prompt_result:
                # This shouldn't happen due to our join, but handle it just in case
                logger.warning(
                    f"No prompt result found for prompt key {prompt_key} "
                    f"in test case {db_test_case.id}",
                )
                continue

            # Convert input variables
            input_variables = [
                InputVariable.model_validate(var)
                for var in db_test_case.prompt_input_variables
            ]

            # Convert eval scores for this prompt result
            eval_executions = []
            for db_eval_score in db_prompt_result.eval_scores:
                eval_input_variables = [
                    InputVariable.model_validate(var)
                    for var in db_eval_score.eval_input_variables
                ]

                # Convert eval results - may be None if not yet executed
                eval_results = None
                if db_eval_score.eval_result_score is not None:
                    eval_results = EvalExecutionResult(
                        score=db_eval_score.eval_result_score,
                        explanation=db_eval_score.eval_result_explanation or "",
                        cost=db_eval_score.eval_result_cost or "0",
                    )

                eval_execution = EvalExecution(
                    eval_name=db_eval_score.eval_name,
                    eval_version=str(db_eval_score.eval_version),
                    eval_input_variables=eval_input_variables,
                    eval_results=eval_results,
                )
                eval_executions.append(eval_execution)

            # Convert prompt output - may be None if not yet executed
            prompt_output = None
            if (
                db_prompt_result.output_content is not None
                or db_prompt_result.output_tool_calls is not None
                or db_prompt_result.output_cost is not None
            ):
                prompt_output = PromptOutput(
                    content=db_prompt_result.output_content or "",
                    tool_calls=db_prompt_result.output_tool_calls or [],
                    cost=db_prompt_result.output_cost or "0",
                )

            # Build the PromptVersionResult
            result = PromptVersionResult(
                status=db_test_case.status,
                dataset_row_id=db_test_case.dataset_row_id,
                prompt_input_variables=input_variables,
                rendered_prompt=db_prompt_result.rendered_prompt,
                output=prompt_output,
                evals=eval_executions,
                total_cost=db_prompt_result.output_cost,
            )
            results.append(result)

        return results, count
