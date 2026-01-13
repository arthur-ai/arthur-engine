import logging
from datetime import datetime
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from db_models.agentic_experiment_models import DatabaseAgenticExperiment
from db_models.agentic_notebook_models import DatabaseAgenticNotebook
from db_models.dataset_models import DatabaseDataset, DatabaseDatasetVersion
from db_models.llm_eval_models import DatabaseLLMEval
from db_models.transform_models import DatabaseTraceTransform
from repositories.agentic_experiment_repository import AgenticExperimentRepository
from schemas.agentic_experiment_schemas import AgenticExperimentListResponse
from schemas.agentic_notebook_schemas import (
    AgenticNotebookDetail,
    AgenticNotebookListResponse,
    AgenticNotebookState,
    AgenticNotebookStateResponse,
    CreateAgenticNotebookRequest,
    SetAgenticNotebookStateRequest,
    UpdateAgenticNotebookRequest,
)
from schemas.internal_schemas import AgenticNotebook

logger = logging.getLogger(__name__)


class AgenticNotebookRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.experiment_repo = AgenticExperimentRepository(db_session)

    def _get_db_notebook(self, notebook_id: str) -> DatabaseAgenticNotebook:
        """Get database agentic notebook by ID or raise 404"""
        db_notebook = (
            self.db_session.query(DatabaseAgenticNotebook)
            .filter(DatabaseAgenticNotebook.id == notebook_id)
            .first()
        )
        if not db_notebook:
            raise HTTPException(
                status_code=404,
                detail=f"Agentic notebook {notebook_id} not found.",
            )
        return db_notebook

    def _validate_notebook_state(
        self,
        task_id: str,
        state: AgenticNotebookState | None,
    ) -> None:
        """Validate that all referenced resources in notebook state exist.

        Only validates resources that are provided (all fields are optional).
        Raises HTTPException with 400 status if validation fails.
        """
        if state is None:
            return

        # Validate dataset exists if provided
        if state.dataset_ref is not None:
            dataset = (
                self.db_session.query(DatabaseDataset)
                .filter(DatabaseDataset.id == state.dataset_ref.id)
                .first()
            )
            if not dataset:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dataset {state.dataset_ref.id} not found",
                )

            dataset_version = (
                self.db_session.query(DatabaseDatasetVersion)
                .filter(
                    DatabaseDatasetVersion.dataset_id == state.dataset_ref.id,
                    DatabaseDatasetVersion.version_number == state.dataset_ref.version,
                )
                .first()
            )
            if not dataset_version:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dataset version {state.dataset_ref.version} not found for dataset {state.dataset_ref.id}",
                )

        # Validate evals if provided
        if state.eval_list:
            for eval_ref in state.eval_list:
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
                    raise HTTPException(
                        status_code=400,
                        detail=f"Eval '{eval_ref.name}' version {eval_ref.version} not found for task {task_id}",
                    )

                # Validate transform exists if provided
                transform = (
                    self.db_session.query(DatabaseTraceTransform)
                    .filter(
                        DatabaseTraceTransform.task_id == task_id,
                        DatabaseTraceTransform.id == eval_ref.transform_id,
                    )
                    .first()
                )
                if not transform:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Transform '{eval_ref.transform_id}' not found for task {task_id}",
                    )

    def create_notebook(
        self,
        task_id: str,
        request: CreateAgenticNotebookRequest,
    ) -> AgenticNotebookDetail:
        """Create a new agentic notebook with optional initial state"""
        # Validate state resources exist
        self._validate_notebook_state(task_id, request.state)

        # Generate notebook ID
        notebook_id = str(uuid4())

        # Create internal notebook from request
        notebook = AgenticNotebook._from_request_model(task_id, notebook_id, request)

        # Convert to database model and save
        db_notebook = notebook._to_database_model()
        self.db_session.add(db_notebook)
        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Created agentic notebook {notebook_id} for task {task_id}")

        # Re-fetch with joinedload for dataset relationship
        db_notebook = self._get_db_notebook(notebook_id)
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook_with_experiments = AgenticNotebook._from_database_model(
            db_notebook,
            [],
            dataset_name,
        )
        return notebook_with_experiments._to_detail_response()

    def get_notebook(self, notebook_id: str) -> AgenticNotebookDetail:
        """Get agentic notebook by ID"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Get experiments and convert to summaries
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]

        # Convert to internal model and return detail response
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = AgenticNotebook._from_database_model(
            db_notebook,
            experiments,
            dataset_name,
        )
        return notebook._to_detail_response()

    def list_notebooks(
        self,
        task_id: str,
        pagination_params: PaginationParameters,
        name_filter: str | None = None,
    ) -> AgenticNotebookListResponse:
        """List agentic notebooks for a task with pagination and optional name filter"""
        # Base query with joinedload for experiments to avoid N+1
        query = (
            self.db_session.query(DatabaseAgenticNotebook)
            .options(joinedload(DatabaseAgenticNotebook.experiments))
            .filter(DatabaseAgenticNotebook.task_id == task_id)
        )

        # Apply name filter if provided (exact match)
        if name_filter is not None:
            query = query.filter(DatabaseAgenticNotebook.name == name_filter)

        # Get total count
        total_count = query.count()

        # Apply sorting
        if pagination_params.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseAgenticNotebook.created_at))
        else:
            query = query.order_by(desc(DatabaseAgenticNotebook.created_at))

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
            # Note: dataset_name not needed for summary response
            notebook = AgenticNotebook._from_database_model(db_notebook, [], None)
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

        return AgenticNotebookListResponse(
            data=notebooks,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )

    def update_notebook(
        self,
        notebook_id: str,
        request: UpdateAgenticNotebookRequest,
    ) -> AgenticNotebookDetail:
        """Update agentic notebook name or description"""
        db_notebook = self._get_db_notebook(notebook_id)

        if request.name is not None:
            db_notebook.name = request.name

        if request.description is not None:
            db_notebook.description = request.description

        db_notebook.updated_at = datetime.now()

        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Updated agentic notebook {notebook_id}")

        # Get experiments and return detail response
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = AgenticNotebook._from_database_model(
            db_notebook,
            experiments,
            dataset_name,
        )
        return notebook._to_detail_response()

    def set_notebook_state(
        self,
        notebook_id: str,
        request: SetAgenticNotebookStateRequest,
    ) -> AgenticNotebookDetail:
        """Set the agentic notebook state"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Validate state resources exist
        self._validate_notebook_state(db_notebook.task_id, request.state)

        # Update state fields
        if request.state.http_template is not None:
            db_notebook.http_template = request.state.http_template.model_dump(
                mode="json",
            )
        else:
            db_notebook.http_template = None

        if request.state.template_variable_mapping is not None:
            db_notebook.template_variable_mapping = [
                mapping.model_dump(mode="json")
                for mapping in request.state.template_variable_mapping
            ]
        else:
            db_notebook.template_variable_mapping = None

        if request.state.dataset_ref is not None:
            db_notebook.dataset_id = request.state.dataset_ref.id
            db_notebook.dataset_version = request.state.dataset_ref.version
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
                eval_ref.model_dump(mode="json") for eval_ref in request.state.eval_list
            ]
        else:
            db_notebook.eval_configs = None

        db_notebook.updated_at = datetime.now()

        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Set state for agentic notebook {notebook_id}")

        # Re-fetch with joinedload for updated dataset relationship
        db_notebook = self._get_db_notebook(notebook_id)
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = AgenticNotebook._from_database_model(
            db_notebook,
            experiments,
            dataset_name,
        )
        return notebook._to_detail_response()

    def get_notebook_state(self, notebook_id: str) -> AgenticNotebookStateResponse:
        """Get the current state of an agentic notebook"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Convert to internal model and return state response
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = AgenticNotebook._from_database_model(db_notebook, [], dataset_name)
        return notebook._to_state_response()

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete an agentic notebook (experiments are kept with notebook_id=NULL)"""
        db_notebook = self._get_db_notebook(notebook_id)

        self.db_session.delete(db_notebook)
        self.db_session.commit()

        logger.info(f"Deleted agentic notebook {notebook_id}")

    def get_notebook_history(
        self,
        notebook_id: str,
        pagination_params: PaginationParameters,
    ) -> AgenticExperimentListResponse:
        """Get paginated history of experiments run from this agentic notebook"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Base query for experiments linked to this notebook
        query = self.db_session.query(DatabaseAgenticExperiment).filter(
            DatabaseAgenticExperiment.notebook_id == notebook_id,
        )

        # Get total count
        total_count = query.count()

        # Apply sorting (most recent first)
        if pagination_params.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseAgenticExperiment.created_at))
        else:
            query = query.order_by(desc(DatabaseAgenticExperiment.created_at))

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

        return AgenticExperimentListResponse(
            data=experiments,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )
