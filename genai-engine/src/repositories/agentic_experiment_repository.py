import logging
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session, joinedload

from db_models.agentic_experiment_models import (
    DatabaseAgenticExperiment,
    DatabaseAgenticExperimentTestCase,
    DatabaseAgenticExperimentTestCaseAgenticResult,
    DatabaseAgenticExperimentTestCaseAgenticResultEvalScore,
)
from db_models.dataset_models import (
    DatabaseDataset,
    DatabaseDatasetVersion,
    DatabaseDatasetVersionRow,
)
from db_models.llm_eval_models import DatabaseLLMEval
from db_models.transform_models import DatabaseTraceTransform
from schemas.agentic_experiment_schemas import (
    AgenticEvalRef,
    AgenticExperimentDetail,
    AgenticExperimentSummary,
    AgenticOutput,
    AgenticResult,
    AgenticSummaryResults,
    AgenticTestCase,
    CreateAgenticExperimentRequest,
    HttpTemplate,
    TemplateVariableMapping,
)
from schemas.base_experiment_schemas import (
    DatasetRef,
    DatasetRefInput,
    EvalExecution,
    EvalExecutionResult,
    ExperimentStatus,
    InputVariable,
    TestCaseStatus,
)
from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
)
from utils.dataset_utils import dataset_row_matches_filter

logger = logging.getLogger(__name__)


class AgenticExperimentRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _get_db_experiment(self, experiment_id: str) -> DatabaseAgenticExperiment:
        """Get database experiment by ID or raise 404"""
        db_experiment = (
            self.db_session.query(DatabaseAgenticExperiment)
            .options(joinedload(DatabaseAgenticExperiment.dataset))
            .filter(DatabaseAgenticExperiment.id == experiment_id)
            .first()
        )
        if not db_experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Agentic experiment {experiment_id} not found.",
            )
        return db_experiment

    def _db_experiment_to_summary(
        self,
        db_experiment: DatabaseAgenticExperiment,
    ) -> AgenticExperimentSummary:
        """Convert database experiment to summary schema"""
        # Convert JSON HTTP template to Pydantic model
        http_template = HttpTemplate.model_validate(db_experiment.http_template)

        # Get dataset name from relationship
        dataset_name = db_experiment.dataset.name

        return AgenticExperimentSummary(
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
            http_template=http_template,
            total_rows=db_experiment.total_rows,
            completed_rows=db_experiment.completed_rows,
            failed_rows=db_experiment.failed_rows,
            total_cost=db_experiment.total_cost,
        )

    def _db_experiment_to_detail(
        self,
        db_experiment: DatabaseAgenticExperiment,
    ) -> AgenticExperimentDetail:
        """Convert database experiment to detail schema"""
        # Convert JSON HTTP template to Pydantic model
        http_template = HttpTemplate.model_validate(db_experiment.http_template)

        # Convert JSON template variable mappings to Pydantic models
        # Note: Request-time parameter mappings are filtered out before saving to DB
        # Request-time parameter values are never stored - they are passed directly to the execution thread
        template_variable_mappings = [
            TemplateVariableMapping.model_validate(mapping)
            for mapping in db_experiment.template_variable_mapping
        ]

        # Convert JSON eval configs to Pydantic models
        eval_list = [
            AgenticEvalRef.model_validate(eval_config)
            for eval_config in db_experiment.eval_configs
        ]

        # Convert summary results to Pydantic model
        summary_results = AgenticSummaryResults.model_validate(
            db_experiment.summary_results or {"eval_summaries": []},
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

        return AgenticExperimentDetail(
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
            http_template=http_template,
            total_rows=db_experiment.total_rows,
            completed_rows=db_experiment.completed_rows,
            failed_rows=db_experiment.failed_rows,
            total_cost=db_experiment.total_cost,
            dataset_ref=DatasetRef(
                id=db_experiment.dataset_id,
                name=dataset_name,
                version=db_experiment.dataset_version,
            ),
            template_variable_mapping=template_variable_mappings,
            eval_list=eval_list,
            dataset_row_filter=dataset_row_filter,
            summary_results=summary_results,
            notebook_id=db_experiment.notebook_id,
        )

    def _db_test_case_to_schema(
        self,
        db_test_case: DatabaseAgenticExperimentTestCase,
    ) -> AgenticTestCase:
        """Convert database test case to schema"""
        # Convert JSON input variables to Pydantic models
        template_input_variables = [
            InputVariable.model_validate(var)
            for var in db_test_case.template_input_variables
        ]

        # Convert agentic result
        agentic_result = None
        if db_test_case.agentic_result:
            # Convert eval scores
            evals = []
            for eval_score in db_test_case.agentic_result.eval_scores:
                eval_input_variables = [
                    InputVariable.model_validate(var)
                    for var in eval_score.eval_input_variables
                ]

                # Convert eval results - may be None if not yet executed
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

            # Convert response output
            response_output = db_test_case.agentic_result.response_output
            agentic_output = None
            if response_output:
                agentic_output = AgenticOutput(
                    response_body=response_output.get("response_body", {}),
                    status_code=response_output.get("status_code"),
                    trace_id=response_output.get("trace_id"),
                )

            agentic_result = AgenticResult(
                request_url=db_test_case.agentic_result.request_url,
                request_headers=db_test_case.agentic_result.request_headers,
                request_body=db_test_case.agentic_result.request_body,
                output=agentic_output,
                evals=evals,
            )

        return AgenticTestCase(
            status=db_test_case.status,
            dataset_row_id=db_test_case.dataset_row_id,
            template_input_variables=template_input_variables,
            agentic_result=agentic_result or AgenticResult(evals=[]),
            total_cost=db_test_case.total_cost,
        )

    def _validate_experiment_references(
        self,
        task_id: str,
        request: CreateAgenticExperimentRequest,
    ) -> Tuple[
        List[Tuple[AgenticEvalRef, DatabaseLLMEval, DatabaseTraceTransform]],
        DatabaseDatasetVersion,
    ]:
        """Validate that all referenced resources exist and return validated configs"""

        # Validate dataset and version exist
        dataset = (
            self.db_session.query(DatabaseDataset)
            .filter(DatabaseDataset.id == request.dataset_ref.id)
            .first()
        )
        if not dataset:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset {request.dataset_ref.id} not found",
            )

        dataset_version = (
            self.db_session.query(DatabaseDatasetVersion)
            .filter(
                DatabaseDatasetVersion.dataset_id == request.dataset_ref.id,
                DatabaseDatasetVersion.version_number == request.dataset_ref.version,
            )
            .first()
        )
        if not dataset_version:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset version {request.dataset_ref.version} not found for dataset {request.dataset_ref.id}",
            )

        # Validate eval versions and transforms exist
        eval_configs = []
        for agentic_eval_ref in request.eval_list:
            # Validate LLM eval exists
            llm_eval = (
                self.db_session.query(DatabaseLLMEval)
                .filter(
                    DatabaseLLMEval.task_id == task_id,
                    DatabaseLLMEval.name == agentic_eval_ref.name,
                    DatabaseLLMEval.version == agentic_eval_ref.version,
                )
                .first()
            )
            if not llm_eval:
                raise HTTPException(
                    status_code=400,
                    detail=f"Eval '{agentic_eval_ref.name}' version {agentic_eval_ref.version} not found for task {task_id}",
                )

            # Validate transform exists
            transform = (
                self.db_session.query(DatabaseTraceTransform)
                .filter(
                    DatabaseTraceTransform.task_id == task_id,
                    DatabaseTraceTransform.id == agentic_eval_ref.transform_id,
                )
                .first()
            )
            if not transform:
                raise HTTPException(
                    status_code=400,
                    detail=f"Transform '{agentic_eval_ref.transform_id}' not found for task {task_id}",
                )

            eval_configs.append((agentic_eval_ref, llm_eval, transform))

        # Validate that all dataset column references exist in the dataset version
        dataset_columns = set(dataset_version.column_names)

        # Validate dataset row filter columns if provided
        if request.dataset_row_filter:
            for filter_item in request.dataset_row_filter:
                if filter_item.column_name not in dataset_columns:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Dataset column '{filter_item.column_name}' referenced in dataset_row_filter not found in dataset version. "
                        f"Available columns: {', '.join(sorted(dataset_columns))}",
                    )

        # Check template variable mappings - validate dataset columns exist and no duplicates
        template_variable_names = []
        for mapping in request.template_variable_mapping:
            template_variable_names.append(mapping.variable_name)
            if mapping.source.type == "dataset_column":
                column_name = mapping.source.dataset_column.name
                if column_name not in dataset_columns:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Dataset column '{column_name}' referenced in template variable mapping not found in dataset version. "
                        f"Available columns: {', '.join(sorted(dataset_columns))}",
                    )

        # Check for duplicate template variable mappings
        duplicate_template_vars = [
            var
            for var in set(template_variable_names)
            if template_variable_names.count(var) > 1
        ]
        if duplicate_template_vars:
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate variable mappings found in template configuration: {', '.join(sorted(duplicate_template_vars))}. "
                f"Each variable must be mapped exactly once.",
            )

        # Check eval variable mappings - validate dataset columns exist and no duplicates
        for agentic_eval_ref, llm_eval, _ in eval_configs:
            eval_variable_names = []
            for mapping in agentic_eval_ref.variable_mapping:
                eval_variable_names.append(mapping.variable_name)
                if mapping.source.type == "dataset_column":
                    column_name = mapping.source.dataset_column.name
                    if column_name not in dataset_columns:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Dataset column '{column_name}' referenced in eval '{agentic_eval_ref.name}' variable mapping not found in dataset version. "
                            f"Available columns: {', '.join(sorted(dataset_columns))}",
                        )

            # Check for duplicate eval variable mappings
            duplicate_eval_vars = [
                var
                for var in set(eval_variable_names)
                if eval_variable_names.count(var) > 1
            ]
            if duplicate_eval_vars:
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate variable mappings found in eval '{agentic_eval_ref.name}' configuration: {', '.join(sorted(duplicate_eval_vars))}. "
                    f"Each variable must be mapped exactly once.",
                )

        # Validate that all eval variables are provided in the configuration
        for agentic_eval_ref, llm_eval, _ in eval_configs:
            provided_eval_variables = {
                mapping.variable_name for mapping in agentic_eval_ref.variable_mapping
            }
            required_variables = set(llm_eval.variables)
            missing_variables = required_variables - provided_eval_variables

            if missing_variables:
                raise HTTPException(
                    status_code=400,
                    detail=f"Eval '{agentic_eval_ref.name}' version {agentic_eval_ref.version} requires variables {sorted(missing_variables)} "
                    f"but they are not provided in the variable mapping. "
                    f"Provided variables: {sorted(provided_eval_variables)}",
                )

        return eval_configs, dataset_version

    def _create_test_cases_for_dataset(
        self,
        experiment_id: str,
        dataset_ref: DatasetRefInput,
        template_variable_mappings: list[TemplateVariableMapping],
        eval_configs: List[
            Tuple[AgenticEvalRef, DatabaseLLMEval, DatabaseTraceTransform]
        ],
        dataset_row_filter: Optional[
            List[NewDatasetVersionRowColumnItemRequest]
        ] = None,
    ) -> int:
        """Create test cases for each row in the dataset version, including agentic results and eval scores"""
        # Get all rows for this dataset version
        dataset_rows = (
            self.db_session.query(DatabaseDatasetVersionRow)
            .filter(
                DatabaseDatasetVersionRow.dataset_id == dataset_ref.id,
                DatabaseDatasetVersionRow.version_number == dataset_ref.version,
            )
            .all()
        )

        # Filter rows based on dataset_row_filter if provided
        filtered_rows = [
            row
            for row in dataset_rows
            if dataset_row_matches_filter(row, dataset_row_filter)
        ]

        # Create a test case for each filtered row
        for row in filtered_rows:
            row_data = row.data  # This is the JSON data for the row

            # Build template input variables from the dataset row data
            # NOTE: Request-time parameters and generated variables are NOT included here
            # They will be provided/resolved at execution time
            template_input_variables = []
            for mapping in template_variable_mappings:
                variable_name = mapping.variable_name

                # Only include dataset column sources in the stored input variables
                if mapping.source.type == "dataset_column":
                    column_name = mapping.source.dataset_column.name
                    column_value = row_data.get(column_name)
                    template_input_variables.append(
                        {
                            "variable_name": variable_name,
                            "value": (
                                str(column_value) if column_value is not None else ""
                            ),
                        },
                    )
                # Skip request_time_parameter and generated - they're resolved at execution

            # Create the test case
            test_case = DatabaseAgenticExperimentTestCase(
                id=str(uuid4()),
                experiment_id=experiment_id,
                dataset_row_id=str(row.id),
                status=TestCaseStatus.QUEUED,
                template_input_variables=template_input_variables,
            )
            self.db_session.add(test_case)

            # Create agentic result (one per test case)
            agentic_result = DatabaseAgenticExperimentTestCaseAgenticResult(
                id=str(uuid4()),
                test_case_id=test_case.id,
                request_url="...waiting to run...",  # Will be filled when experiment runs
                request_headers={},  # Will be filled when experiment runs
                request_body="",  # Will be filled when experiment runs
                response_output={},  # Will be filled when experiment runs
            )
            self.db_session.add(agentic_result)

            # Create eval score entries for each eval configuration
            for agentic_eval_ref, llm_eval, _ in eval_configs:
                # Build eval input variables based on the mapping
                eval_input_variables = []
                for mapping in agentic_eval_ref.variable_mapping:
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
                        # Mark as placeholder - will be filled from agent output or transform when experiment runs
                        eval_input_variables.append(
                            {
                                "variable_name": variable_name,
                                "value": "...waiting for response...",  # Will be filled when experiment runs
                            },
                        )

                eval_score = DatabaseAgenticExperimentTestCaseAgenticResultEvalScore(
                    id=str(uuid4()),
                    agentic_result_id=agentic_result.id,
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
        request: CreateAgenticExperimentRequest,
    ) -> AgenticExperimentSummary:
        """Create a new agentic experiment with test cases"""
        # Validate all references
        eval_configs, dataset_version = self._validate_experiment_references(
            task_id,
            request,
        )

        # Convert HTTP template to JSON-serializable format
        http_template_json = request.http_template.model_dump(mode="json")

        # Convert template variable mappings to JSON (request-time parameters will be
        # automatically filtered out by the DB model validator)
        template_variable_mapping_json = [
            mapping.model_dump(mode="json")
            for mapping in request.template_variable_mapping
        ]

        # Convert eval configs to JSON-serializable format
        eval_configs_json = [
            agentic_eval_ref.model_dump(mode="json")
            for agentic_eval_ref, _, _ in eval_configs
        ]

        # Convert dataset row filter to JSON-serializable format if present
        dataset_row_filter_json = None
        if request.dataset_row_filter:
            dataset_row_filter_json = [
                filter_item.model_dump(mode="python")
                for filter_item in request.dataset_row_filter
            ]

        # Create the experiment
        # NOTE: request_time_parameters are NOT stored in the database - they are passed
        # directly to the execution thread for security reasons
        db_experiment = DatabaseAgenticExperiment(
            id=experiment_id,
            task_id=task_id,
            name=request.name,
            description=request.description,
            status=ExperimentStatus.QUEUED,
            http_template=http_template_json,
            template_variable_mapping=template_variable_mapping_json,
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
            template_variable_mappings=request.template_variable_mapping,
            eval_configs=eval_configs,
            dataset_row_filter=request.dataset_row_filter,
        )

        # Update total rows
        db_experiment.total_rows = total_rows
        self.db_session.commit()
        self.db_session.refresh(db_experiment)

        return self._db_experiment_to_summary(db_experiment)

    def get_experiment(self, experiment_id: str) -> AgenticExperimentDetail:
        """Get an agentic experiment by ID"""
        db_experiment = self._get_db_experiment(experiment_id)
        return self._db_experiment_to_detail(db_experiment)

    def list_experiments(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters,
        search: Optional[str] = None,
        dataset_id: Optional[UUID] = None,
    ) -> Tuple[List[AgenticExperimentSummary], int]:
        """List agentic experiments for a task with optional filtering and pagination"""
        query = self.db_session.query(DatabaseAgenticExperiment).filter(
            DatabaseAgenticExperiment.task_id == task_id,
        )

        # Apply search filter if provided
        if search:
            search_filter = or_(
                DatabaseAgenticExperiment.name.ilike(f"%{search}%"),
                DatabaseAgenticExperiment.description.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        # Apply dataset filter if provided
        if dataset_id:
            query = query.filter(DatabaseAgenticExperiment.dataset_id == dataset_id)

        # Apply sorting
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseAgenticExperiment.created_at))
        elif pagination_parameters.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseAgenticExperiment.created_at))

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        db_experiments = (
            query.options(joinedload(DatabaseAgenticExperiment.dataset))
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
    ) -> List[DatabaseAgenticExperimentTestCase]:
        query = self.db_session.query(DatabaseAgenticExperimentTestCase).filter(
            DatabaseAgenticExperimentTestCase.experiment_id == experiment_id,
        )
        if status_filter:
            query = query.filter(
                DatabaseAgenticExperimentTestCase.status == status_filter,
            )
        return query.all()

    def _get_db_test_case(
        self,
        test_case_id: str,
    ) -> Optional[DatabaseAgenticExperimentTestCase]:
        test_case = (
            self.db_session.query(DatabaseAgenticExperimentTestCase)
            .filter_by(id=test_case_id)
            .first()
        )
        return test_case

    def get_test_cases(
        self,
        experiment_id: str,
        pagination_parameters: PaginationParameters,
    ) -> Tuple[List[AgenticTestCase], int]:
        """Get test cases for an agentic experiment with pagination"""
        # Verify experiment exists
        self._get_db_experiment(experiment_id)

        # Query test cases
        query = self.db_session.query(DatabaseAgenticExperimentTestCase).filter(
            DatabaseAgenticExperimentTestCase.experiment_id == experiment_id,
        )

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        db_test_cases = (
            query.options(
                joinedload(DatabaseAgenticExperimentTestCase.agentic_result).joinedload(
                    DatabaseAgenticExperimentTestCaseAgenticResult.eval_scores,
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

    def attach_notebook_to_experiment(
        self,
        experiment_id: str,
        notebook_id: str,
    ) -> AgenticExperimentSummary:
        """Attach an agentic notebook to an experiment."""
        db_experiment = self._get_db_experiment(experiment_id)

        # Update notebook_id
        db_experiment.notebook_id = notebook_id
        self.db_session.commit()

        # Return updated summary
        return self._db_experiment_to_summary(db_experiment)

    def delete_experiment(self, experiment_id: str) -> None:
        """Delete an experiment and its test cases (cascaded)"""
        db_experiment = self._get_db_experiment(experiment_id)
        self.db_session.delete(db_experiment)
        self.db_session.commit()
