import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from db_models.notebook_models import DatabaseNotebook
from db_models.prompt_experiment_models import DatabasePromptExperiment
from repositories.prompt_experiment_repository import PromptExperimentRepository
from schemas.notebook_schemas import (
    CreateNotebookRequest,
    Notebook,
    NotebookDetail,
    NotebookState,
    NotebookSummary,
    NotebookValidationResponse,
    RunNotebookRequest,
    SetNotebookStateRequest,
    UpdateNotebookRequest,
)
from schemas.prompt_experiment_schemas import (
    CreatePromptExperimentRequest,
    PromptExperimentSummary,
)
from services.experiment_executor import ExperimentExecutor

logger = logging.getLogger(__name__)


class NotebookRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.experiment_repo = PromptExperimentRepository(db_session)

    def _get_db_notebook(self, notebook_id: str) -> DatabaseNotebook:
        """Get database notebook by ID or raise 404"""
        db_notebook = (
            self.db_session.query(DatabaseNotebook)
            .filter(DatabaseNotebook.id == notebook_id)
            .first()
        )
        if not db_notebook:
            raise HTTPException(
                status_code=404,
                detail=f"Notebook {notebook_id} not found.",
            )
        return db_notebook


    def create_notebook(
        self, task_id: str, notebook_id: str, request: CreateNotebookRequest
    ) -> NotebookDetail:
        """Create a new notebook with optional initial state"""
        # Create internal notebook from request
        notebook = Notebook._from_request_model(task_id, notebook_id, request)

        # Convert to database model and save
        db_notebook = notebook._to_database_model()
        self.db_session.add(db_notebook)
        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Created notebook {notebook_id} for task {task_id}")

        # Return detail response (no experiments yet)
        notebook_with_experiments = Notebook._from_database_model(db_notebook, [])
        return notebook_with_experiments._to_detail_response()

    def get_notebook(self, notebook_id: str) -> NotebookDetail:
        """Get notebook by ID"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Get experiments and convert to summaries
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]

        # Convert to internal model and return detail response
        notebook = Notebook._from_database_model(db_notebook, experiments)
        return notebook._to_detail_response()

    def list_notebooks(
        self, task_id: str, pagination_params: PaginationParameters
    ) -> Tuple[List[NotebookSummary], int]:
        """List notebooks for a task with pagination"""
        # Base query
        query = self.db_session.query(DatabaseNotebook).filter(
            DatabaseNotebook.task_id == task_id
        )

        # Get total count
        total_count = query.count()

        # Apply sorting
        if pagination_params.sort_method == PaginationSortMethod.ASC:
            query = query.order_by(asc(DatabaseNotebook.created_at))
        else:
            query = query.order_by(desc(DatabaseNotebook.created_at))

        # Apply pagination
        offset = pagination_params.page * pagination_params.page_size
        query = query.offset(offset).limit(pagination_params.page_size)

        # Execute query
        db_notebooks = query.all()

        # Convert to summaries using internal schema
        notebooks = []
        for db_notebook in db_notebooks:
            # Calculate run statistics
            run_count = len(db_notebook.experiments)
            latest_run_id = None
            latest_run_status = None

            if db_notebook.experiments:
                latest_experiment = db_notebook.experiments[0]  # Already ordered by created_at desc
                latest_run_id = latest_experiment.id
                latest_run_status = latest_experiment.status

            # Convert to internal model and generate summary
            notebook = Notebook._from_database_model(db_notebook, [])
            summary = notebook._to_summary_response(
                run_count=run_count,
                latest_run_id=latest_run_id,
                latest_run_status=latest_run_status,
            )
            notebooks.append(summary)

        return notebooks, total_count

    def update_notebook(
        self, notebook_id: str, request: UpdateNotebookRequest
    ) -> NotebookDetail:
        """Update notebook name or description"""
        db_notebook = self._get_db_notebook(notebook_id)

        if request.name is not None:
            db_notebook.name = request.name

        if request.description is not None:
            db_notebook.description = request.description

        db_notebook.updated_at = datetime.now()

        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Updated notebook {notebook_id}")

        # Get experiments and return detail response
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]
        notebook = Notebook._from_database_model(db_notebook, experiments)
        return notebook._to_detail_response()

    def set_notebook_state(
        self, notebook_id: str, request: SetNotebookStateRequest
    ) -> NotebookDetail:
        """Set the notebook state"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Update state fields
        if request.state.prompt_configs is not None:
            db_notebook.prompt_configs = [
                config.model_dump() for config in request.state.prompt_configs
            ]
        else:
            db_notebook.prompt_configs = None

        if request.state.prompt_variable_mapping is not None:
            db_notebook.prompt_variable_mapping = [
                mapping.model_dump() for mapping in request.state.prompt_variable_mapping
            ]
        else:
            db_notebook.prompt_variable_mapping = None

        if request.state.dataset_ref is not None:
            db_notebook.dataset_id = str(request.state.dataset_ref.id)
            db_notebook.dataset_version = request.state.dataset_ref.version
        else:
            db_notebook.dataset_id = None
            db_notebook.dataset_version = None

        if request.state.eval_list is not None:
            db_notebook.eval_configs = [
                eval_ref.model_dump() for eval_ref in request.state.eval_list
            ]
        else:
            db_notebook.eval_configs = None

        db_notebook.updated_at = datetime.now()

        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Set state for notebook {notebook_id}")

        # Get experiments and return detail response
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]
        notebook = Notebook._from_database_model(db_notebook, experiments)
        return notebook._to_detail_response()

    def get_notebook_state(self, notebook_id: str) -> NotebookState:
        """Get the current state of a notebook"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Convert to internal model and return state response
        notebook = Notebook._from_database_model(db_notebook, [])
        return notebook._to_state_response()

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete a notebook (experiments are kept with notebook_id=NULL)"""
        db_notebook = self._get_db_notebook(notebook_id)

        self.db_session.delete(db_notebook)
        self.db_session.commit()

        logger.info(f"Deleted notebook {notebook_id}")

    def validate_notebook_state(self, notebook_id: str) -> NotebookValidationResponse:
        """
        Check if notebook state is complete and valid for running.
        Returns validation result with list of errors if invalid.
        """
        db_notebook = self._get_db_notebook(notebook_id)
        errors = []

        # Check required fields are present and non-null
        if not db_notebook.prompt_configs:
            errors.append("prompt_configs is required")
        elif len(db_notebook.prompt_configs) == 0:
            errors.append("At least one prompt configuration is required")

        if not db_notebook.prompt_variable_mapping:
            errors.append("prompt_variable_mapping is required")

        if not db_notebook.dataset_id or not db_notebook.dataset_version:
            errors.append("dataset_ref is required")

        if not db_notebook.eval_configs:
            errors.append("eval_list is required")
        elif len(db_notebook.eval_configs) == 0:
            errors.append("At least one evaluation is required")

        # If basic validation passes, try to construct an experiment request
        # to leverage existing validation logic
        if not errors:
            try:
                # Convert to internal model and get state
                notebook = Notebook._from_database_model(db_notebook, [])
                state = notebook._to_state_response()

                # Construct CreatePromptExperimentRequest to validate
                experiment_request = CreatePromptExperimentRequest(
                    name="Validation Test",
                    description=None,
                    prompt_configs=state.prompt_configs,
                    prompt_variable_mapping=state.prompt_variable_mapping,
                    dataset_ref=state.dataset_ref,
                    eval_list=state.eval_list,
                )
                # If we get here, the request is valid
            except Exception as e:
                errors.append(f"State validation failed: {str(e)}")

        valid = len(errors) == 0
        return NotebookValidationResponse(valid=valid, errors=errors)

    def run_notebook(
        self, notebook_id: str, request: RunNotebookRequest
    ) -> PromptExperimentSummary:
        """
        Create and execute a PromptExperiment from the notebook's current state.
        Validates state is complete, creates experiment, links to notebook, executes.
        """
        # Validate state is complete
        validation = self.validate_notebook_state(notebook_id)
        if not validation.valid:
            raise HTTPException(
                status_code=400,
                detail=f"Notebook state is invalid: {', '.join(validation.errors)}",
            )

        db_notebook = self._get_db_notebook(notebook_id)

        # Convert to internal model and get state
        notebook = Notebook._from_database_model(db_notebook, [])
        state = notebook._to_state_response()

        # Generate experiment name if not provided
        experiment_name = request.experiment_name
        if not experiment_name:
            run_count = len(db_notebook.experiments) + 1
            experiment_name = f"{db_notebook.name} - Run {run_count}"

        # Create experiment request from notebook state
        experiment_request = CreatePromptExperimentRequest(
            name=experiment_name,
            description=request.experiment_description,
            prompt_configs=state.prompt_configs,
            prompt_variable_mapping=state.prompt_variable_mapping,
            dataset_ref=state.dataset_ref,
            eval_list=state.eval_list,
        )

        # Create experiment with notebook_id link
        experiment_id = str(uuid4())
        experiment_summary = self.experiment_repo.create_prompt_experiment(
            task_id=db_notebook.task_id,
            experiment_id=experiment_id,
            request=experiment_request,
            notebook_id=notebook_id,  # Link to notebook
        )

        # Trigger experiment execution
        executor = ExperimentExecutor(self.db_session)
        executor.execute_experiment(experiment_id)

        logger.info(f"Running notebook {notebook_id} as experiment {experiment_id}")
        return experiment_summary

    def get_notebook_history(
        self, notebook_id: str, pagination_params: PaginationParameters
    ) -> Tuple[List[PromptExperimentSummary], int]:
        """Get paginated history of experiments run from this notebook"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Base query for experiments linked to this notebook
        query = self.db_session.query(DatabasePromptExperiment).filter(
            DatabasePromptExperiment.notebook_id == notebook_id
        )

        # Get total count
        total_count = query.count()

        # Apply sorting (most recent first)
        if pagination_params.sort_method == PaginationSortMethod.ASC:
            query = query.order_by(asc(DatabasePromptExperiment.created_at))
        else:
            query = query.order_by(desc(DatabasePromptExperiment.created_at))

        # Apply pagination
        offset = pagination_params.page * pagination_params.page_size
        query = query.offset(offset).limit(pagination_params.page_size)

        # Execute query
        db_experiments = query.all()

        # Convert to summaries
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_experiments
        ]

        return experiments, total_count
