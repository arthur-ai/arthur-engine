import logging
from datetime import datetime
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from db_models.notebook_models import DatabaseNotebook
from db_models.prompt_experiment_models import DatabasePromptExperiment
from repositories.prompt_experiment_repository import PromptExperimentRepository
from schemas.notebook_schemas import (
    CreateNotebookRequest,
    Notebook,
    NotebookDetail,
    NotebookListResponse,
    NotebookState,
    SetNotebookStateRequest,
    UpdateNotebookRequest,
)
from schemas.prompt_experiment_schemas import (
    PromptExperimentListResponse,
)

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
        self,
        task_id: str,
        request: CreateNotebookRequest,
    ) -> NotebookDetail:
        """Create a new notebook with optional initial state"""
        # Generate notebook ID
        notebook_id = str(uuid4())

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
        self,
        task_id: str,
        pagination_params: PaginationParameters,
        name_filter: str | None = None,
    ) -> NotebookListResponse:
        """List notebooks for a task with pagination and optional name filter"""
        # Base query
        query = self.db_session.query(DatabaseNotebook).filter(
            DatabaseNotebook.task_id == task_id,
        )

        # Apply name filter if provided (exact match)
        if name_filter is not None:
            query = query.filter(DatabaseNotebook.name == name_filter)

        # Get total count
        total_count = query.count()

        # Apply sorting
        if pagination_params.sort == PaginationSortMethod.ASCENDING:
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
                latest_experiment = db_notebook.experiments[
                    0
                ]  # Already ordered by created_at desc
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

        # Calculate pagination metadata
        page = pagination_params.page
        page_size = pagination_params.page_size
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 0
        )

        return NotebookListResponse(
            data=notebooks,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )

    def update_notebook(
        self,
        notebook_id: str,
        request: UpdateNotebookRequest,
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
        self,
        notebook_id: str,
        request: SetNotebookStateRequest,
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
                mapping.model_dump()
                for mapping in request.state.prompt_variable_mapping
            ]
        else:
            db_notebook.prompt_variable_mapping = None

        if request.state.dataset_ref is not None:
            db_notebook.dataset_id = str(request.state.dataset_ref.id)
            db_notebook.dataset_version = request.state.dataset_ref.version
            db_notebook.dataset_name = request.state.dataset_ref.name
        else:
            db_notebook.dataset_id = None
            db_notebook.dataset_version = None

        if request.state.dataset_row_filter is not None:
            db_notebook.dataset_row_filter = [
                filter_item.model_dump()
                for filter_item in request.state.dataset_row_filter
            ]
        else:
            db_notebook.dataset_row_filter = None

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

    def get_notebook_history(
        self,
        notebook_id: str,
        pagination_params: PaginationParameters,
    ) -> PromptExperimentListResponse:
        """Get paginated history of experiments run from this notebook"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Base query for experiments linked to this notebook
        query = self.db_session.query(DatabasePromptExperiment).filter(
            DatabasePromptExperiment.notebook_id == notebook_id,
        )

        # Get total count
        total_count = query.count()

        # Apply sorting (most recent first)
        if pagination_params.sort == PaginationSortMethod.ASCENDING:
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

        # Calculate pagination metadata
        page = pagination_params.page
        page_size = pagination_params.page_size
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 0
        )

        return PromptExperimentListResponse(
            data=experiments,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )
