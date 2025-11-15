import logging
from datetime import datetime
from typing import List, Optional, Tuple

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from db_models.prompt_experiment_models import (
    DatabasePromptExperiment,
    DatabasePromptExperimentTestCase,
)
from schemas.prompt_experiment_schemas import (
    CreatePromptExperimentRequest,
    DatasetRef,
    EvalRef,
    ExperimentStatus,
    InputVariable,
    PromptExperimentDetail,
    PromptExperimentSummary,
    PromptRef,
    PromptResult,
    SummaryResults,
    TestCase,
    VariableMapping,
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
        # Convert JSON variable mappings to Pydantic models
        variable_mappings = [
            VariableMapping(**mapping) for mapping in db_experiment.prompt_variable_mapping
        ]

        # Convert JSON eval configs to Pydantic models
        eval_list = [EvalRef(**eval_config) for eval_config in db_experiment.eval_configs]

        # Convert summary results to Pydantic model
        summary_results = SummaryResults(**(db_experiment.summary_results or {"prompt_eval_summaries": []}))

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
                variable_mapping=variable_mappings,
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
            InputVariable(**var) for var in db_test_case.prompt_input_variables
        ]

        # Convert JSON prompt results to Pydantic models
        prompt_results = [
            PromptResult(**result) for result in db_test_case.prompt_results
        ]

        return TestCase(
            status=db_test_case.status,
            retries=db_test_case.retries,
            dataset_row_id=db_test_case.dataset_row_id,
            prompt_input_variables=input_variables,
            prompt_results=prompt_results,
        )

    def create_experiment(
        self,
        task_id: str,
        experiment_id: str,
        request: CreatePromptExperimentRequest,
    ) -> PromptExperimentSummary:
        """Create a new experiment"""
        db_experiment = DatabasePromptExperiment(
            id=experiment_id,
            task_id=task_id,
            name=request.name,
            description=request.description,
            status=ExperimentStatus.QUEUED,
            prompt_name=request.prompt_ref.name,
            prompt_versions=request.prompt_ref.version_list,
            dataset_id=request.dataset_ref.id,
            dataset_version=request.dataset_ref.version,
            prompt_variable_mapping=[
                mapping.model_dump() for mapping in request.prompt_ref.variable_mapping
            ],
            eval_configs=[eval_ref.model_dump() for eval_ref in request.eval_list],
            total_rows=0,
            completed_rows=0,
            failed_rows=0,
        )

        self.db_session.add(db_experiment)
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

    def update_experiment_status(
        self,
        experiment_id: str,
        status: ExperimentStatus,
        finished_at: Optional[datetime] = None,
    ) -> None:
        """Update experiment status"""
        db_experiment = self._get_db_experiment(experiment_id)
        db_experiment.status = status
        if finished_at:
            db_experiment.finished_at = finished_at
        self.db_session.commit()

    def update_experiment_counts(
        self,
        experiment_id: str,
        total_rows: Optional[int] = None,
        completed_rows: Optional[int] = None,
        failed_rows: Optional[int] = None,
    ) -> None:
        """Update experiment row counts"""
        db_experiment = self._get_db_experiment(experiment_id)
        if total_rows is not None:
            db_experiment.total_rows = total_rows
        if completed_rows is not None:
            db_experiment.completed_rows = completed_rows
        if failed_rows is not None:
            db_experiment.failed_rows = failed_rows
        self.db_session.commit()

    def update_experiment_summary_results(
        self, experiment_id: str, summary_results: dict
    ) -> None:
        """Update experiment summary results"""
        db_experiment = self._get_db_experiment(experiment_id)
        db_experiment.summary_results = summary_results
        self.db_session.commit()

    # Test case methods
    def create_test_case(
        self,
        test_case_id: str,
        experiment_id: str,
        dataset_row_id: str,
        prompt_input_variables: list,
    ) -> None:
        """Create a new test case"""
        db_test_case = DatabasePromptExperimentTestCase(
            id=test_case_id,
            experiment_id=experiment_id,
            dataset_row_id=dataset_row_id,
            prompt_input_variables=prompt_input_variables,
            prompt_results=[],
        )
        self.db_session.add(db_test_case)
        self.db_session.commit()

    def get_test_cases(
        self,
        experiment_id: str,
        pagination_params: PaginationParameters,
    ) -> Tuple[List[TestCase], int]:
        """Get paginated test cases for an experiment"""
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

    def update_test_case_results(
        self,
        test_case_id: str,
        prompt_results: list,
        status: Optional[str] = None,
    ) -> None:
        """Update test case results"""
        db_test_case = (
            self.db_session.query(DatabasePromptExperimentTestCase)
            .filter(DatabasePromptExperimentTestCase.id == test_case_id)
            .first()
        )
        if not db_test_case:
            raise HTTPException(
                status_code=404,
                detail=f"Test case {test_case_id} not found.",
            )

        db_test_case.prompt_results = prompt_results
        if status:
            db_test_case.status = status
        db_test_case.updated_at = datetime.now()
        self.db_session.commit()
