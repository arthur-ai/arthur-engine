import logging
from typing import List, Optional, Tuple
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc
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
from schemas.prompt_experiment_schemas import TestCaseStatus
from schemas.prompt_experiment_schemas import (
    CreatePromptExperimentRequest,
    DatasetRef,
    EvalRef,
    EvalVariableMapping,
    ExperimentStatus,
    InputVariable,
    PromptExperimentDetail,
    PromptExperimentSummary,
    PromptRef,
    PromptResult,
    PromptVariableMapping,
    SummaryResults,
    TestCase,
)

logger = logging.getLogger(__name__)


class PromptExperimentRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

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
        self, db_experiment: DatabasePromptExperiment
    ) -> PromptExperimentSummary:
        """Convert database experiment to summary schema"""
        return PromptExperimentSummary(
            id=db_experiment.id,
            name=db_experiment.name,
            description=db_experiment.description,
            created_at=db_experiment.created_at.isoformat() if db_experiment.created_at else None,
            finished_at=db_experiment.finished_at.isoformat() if db_experiment.finished_at else None,
            status=db_experiment.status,
            prompt_name=db_experiment.prompt_name,
            total_rows=db_experiment.total_rows,
        )

    def _db_experiment_to_detail(
        self, db_experiment: DatabasePromptExperiment
    ) -> PromptExperimentDetail:
        """Convert database experiment to detail schema"""
        # Convert JSON prompt variable mappings to Pydantic models
        prompt_variable_mappings = [
            PromptVariableMapping.model_validate(mapping) for mapping in db_experiment.prompt_variable_mapping
        ]

        # Convert JSON eval configs to Pydantic models
        eval_list = [EvalRef.model_validate(eval_config) for eval_config in db_experiment.eval_configs]

        # Convert summary results to Pydantic model
        summary_results = SummaryResults.model_validate(db_experiment.summary_results or {"prompt_eval_summaries": []})

        return PromptExperimentDetail(
            id=db_experiment.id,
            name=db_experiment.name,
            description=db_experiment.description,
            created_at=db_experiment.created_at.isoformat() if db_experiment.created_at else None,
            finished_at=db_experiment.finished_at.isoformat() if db_experiment.finished_at else None,
            status=db_experiment.status,
            prompt_name=db_experiment.prompt_name,
            dataset_ref=DatasetRef(
                id=db_experiment.dataset_id,
                version=db_experiment.dataset_version,
            ),
            prompt_ref=PromptRef(
                name=db_experiment.prompt_name,
                version_list=db_experiment.prompt_versions,
                variable_mapping=prompt_variable_mappings,
            ),
            eval_list=eval_list,
            summary_results=summary_results,
        )

    def _db_test_case_to_schema(
        self, db_test_case: DatabasePromptExperimentTestCase
    ) -> TestCase:
        """Convert database test case to schema"""
        # Convert JSON input variables to Pydantic models
        input_variables = [
            InputVariable.model_validate(var) for var in db_test_case.prompt_input_variables
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

                from schemas.prompt_experiment_schemas import EvalExecution, EvalResults
                eval_execution = EvalExecution(
                    eval_name=db_eval_score.eval_name,
                    eval_version=str(db_eval_score.eval_version),
                    eval_input_variables=eval_input_variables,
                    eval_results=EvalResults.model_validate(db_eval_score.eval_results),
                )
                eval_executions.append(eval_execution)

            # Convert prompt output
            from schemas.prompt_experiment_schemas import PromptOutput
            prompt_output = PromptOutput.model_validate(db_prompt_result.output)

            # Build the full prompt result
            prompt_result = PromptResult(
                name=db_prompt_result.name,
                version=str(db_prompt_result.version),
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
        )

    def _validate_experiment_references(
        self,
        task_id: str,
        request: CreatePromptExperimentRequest,
    ) -> Tuple[List[DatabaseAgenticPrompt], List[Tuple[EvalRef, DatabaseLLMEval]], DatabaseDatasetVersion]:
        """Validate that all referenced resources exist and return them"""
        # Validate task exists
        task = self.db_session.query(DatabaseTask).filter(
            DatabaseTask.id == task_id
        ).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Validate dataset and version exist
        dataset = self.db_session.query(DatabaseDataset).filter(
            DatabaseDataset.id == request.dataset_ref.id
        ).first()
        if not dataset:
            raise ValueError(f"Dataset {request.dataset_ref.id} not found")

        dataset_version = self.db_session.query(DatabaseDatasetVersion).filter(
            DatabaseDatasetVersion.dataset_id == request.dataset_ref.id,
            DatabaseDatasetVersion.version_number == request.dataset_ref.version,
        ).first()
        if not dataset_version:
            raise ValueError(
                f"Dataset version {request.dataset_ref.version} not found for dataset {request.dataset_ref.id}"
            )

        # Validate prompt versions exist and collect their variables
        prompt_versions = []
        for version in request.prompt_ref.version_list:
            prompt = self.db_session.query(DatabaseAgenticPrompt).filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == request.prompt_ref.name,
                DatabaseAgenticPrompt.version == version,
            ).first()
            if not prompt:
                raise ValueError(
                    f"Prompt '{request.prompt_ref.name}' version {version} not found for task {task_id}"
                )
            prompt_versions.append(prompt)

        # Validate eval versions exist and collect their variables
        llm_evals = []
        for eval_ref in request.eval_list:
            llm_eval = self.db_session.query(DatabaseLLMEval).filter(
                DatabaseLLMEval.task_id == task_id,
                DatabaseLLMEval.name == eval_ref.name,
                DatabaseLLMEval.version == eval_ref.version,
            ).first()
            if not llm_eval:
                raise ValueError(
                    f"Eval '{eval_ref.name}' version {eval_ref.version} not found for task {task_id}"
                )
            llm_evals.append((eval_ref, llm_eval))

        # Validate that all dataset column references exist in the dataset version
        dataset_columns = set(dataset_version.column_names)

        # Check prompt variable mappings - validate dataset columns exist
        # (Type enforcement is handled by schema - PromptVariableMapping only accepts DatasetColumnVariableSource)
        for mapping in request.prompt_ref.variable_mapping:
            column_name = mapping.source.dataset_column.name
            if column_name not in dataset_columns:
                raise ValueError(
                    f"Dataset column '{column_name}' referenced in prompt variable mapping not found in dataset version. "
                    f"Available columns: {', '.join(sorted(dataset_columns))}"
                )

        # Check eval variable mappings - only validate dataset_column type
        for eval_ref in request.eval_list:
            for mapping in eval_ref.variable_mapping:
                if mapping.source.type == "dataset_column":
                    column_name = mapping.source.dataset_column.name
                    if column_name not in dataset_columns:
                        raise ValueError(
                            f"Dataset column '{column_name}' referenced in eval '{eval_ref.name}' variable mapping not found in dataset version. "
                            f"Available columns: {', '.join(sorted(dataset_columns))}"
                        )

        # Validate that all prompt variables are provided in the configuration
        provided_prompt_variables = {mapping.variable_name for mapping in request.prompt_ref.variable_mapping}

        for prompt in prompt_versions:
            required_variables = set(prompt.variables)
            missing_variables = required_variables - provided_prompt_variables

            if missing_variables:
                raise ValueError(
                    f"Prompt '{request.prompt_ref.name}' version {prompt.version} requires variables {sorted(missing_variables)} "
                    f"but they are not provided in the variable mapping. "
                    f"Provided variables: {sorted(provided_prompt_variables)}"
                )

        # Validate that all eval variables are provided in the configuration
        for eval_ref, llm_eval in llm_evals:
            provided_eval_variables = {mapping.variable_name for mapping in eval_ref.variable_mapping}
            required_variables = set(llm_eval.variables)
            missing_variables = required_variables - provided_eval_variables

            if missing_variables:
                raise ValueError(
                    f"Eval '{eval_ref.name}' version {eval_ref.version} requires variables {sorted(missing_variables)} "
                    f"but they are not provided in the variable mapping. "
                    f"Provided variables: {sorted(provided_eval_variables)}"
                )

        return prompt_versions, llm_evals, dataset_version

    def _create_test_cases_for_dataset(
        self,
        experiment_id: str,
        dataset_ref: DatasetRef,
        prompt_variable_mappings: list[PromptVariableMapping],
        prompt_versions: List[DatabaseAgenticPrompt],
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

                prompt_input_variables.append({
                    "variable_name": variable_name,
                    "value": column_value,
                })

            # Create the test case
            test_case = DatabasePromptExperimentTestCase(
                id=str(uuid4()),
                experiment_id=experiment_id,
                dataset_row_id=str(row.id),
                status=TestCaseStatus.QUEUED,
                prompt_input_variables=prompt_input_variables,
            )
            self.db_session.add(test_case)

            # Create prompt results for each prompt version in this test case
            for prompt in prompt_versions:
                prompt_result = DatabasePromptExperimentTestCasePromptResult(
                    id=str(uuid4()),
                    test_case_id=test_case.id,
                    name=prompt.name,
                    version=prompt.version,
                    rendered_prompt="",  # Will be filled when experiment runs
                    output={},  # Will be filled when experiment runs
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
                            eval_input_variables.append({
                                "variable_name": variable_name,
                                "value": column_value,
                            })
                        elif mapping.source.type == "experiment_output":
                            # Mark as placeholder - will be filled from prompt output when experiment runs
                            eval_input_variables.append({
                                "variable_name": variable_name,
                                "value": None,  # Will be filled when experiment runs
                            })

                    eval_score = DatabasePromptExperimentTestCasePromptResultEvalScore(
                        id=str(uuid4()),
                        prompt_result_id=prompt_result.id,
                        eval_name=llm_eval.name,
                        eval_version=llm_eval.version,
                        eval_input_variables=eval_input_variables,
                        eval_results={},  # Will be filled when experiment runs
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
        # Validate all references exist and get validated objects
        prompt_versions, eval_configs, dataset_version = self._validate_experiment_references(task_id, request)

        # Create the experiment
        db_experiment = DatabasePromptExperiment(
            id=experiment_id,
            task_id=task_id,
            name=request.name,
            description=request.description,
            status=ExperimentStatus.QUEUED,
            prompt_name=request.prompt_ref.name,
            prompt_versions=request.prompt_ref.version_list,
            dataset_id=str(request.dataset_ref.id),
            dataset_version=request.dataset_ref.version,
            prompt_variable_mapping=[
                mapping.model_dump() for mapping in request.prompt_ref.variable_mapping
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
            request.prompt_ref.variable_mapping,
            prompt_versions,
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
    ) -> Tuple[List[PromptExperimentSummary], int]:
        """List experiments for a task with optional filtering"""
        base_query = self.db_session.query(DatabasePromptExperiment).filter(
            DatabasePromptExperiment.task_id == task_id
        )

        # Apply status filter if provided
        if status_filter:
            base_query = base_query.filter(
                DatabasePromptExperiment.status == status_filter
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
            pagination_params.page * pagination_params.page_size
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
            DatabasePromptExperimentTestCase.experiment_id == experiment_id
        )

        # Apply sorting - sort by created_at field
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            base_query = base_query.order_by(
                desc(DatabasePromptExperimentTestCase.created_at)
            )
        else:
            base_query = base_query.order_by(
                asc(DatabasePromptExperimentTestCase.created_at)
            )

        # Calculate total count
        count = base_query.count()

        # Apply pagination
        base_query = base_query.offset(
            pagination_params.page * pagination_params.page_size
        )
        db_test_cases = base_query.limit(pagination_params.page_size).all()

        return [
            self._db_test_case_to_schema(db_tc) for db_tc in db_test_cases
        ], count
