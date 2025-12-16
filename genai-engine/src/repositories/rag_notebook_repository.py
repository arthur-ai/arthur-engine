import logging
from datetime import datetime
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from db_models.dataset_models import DatabaseDataset, DatabaseDatasetVersion
from db_models.llm_eval_models import DatabaseLLMEval
from db_models.rag_experiment_models import DatabaseRagExperiment
from db_models.rag_notebook_models import DatabaseRagNotebook
from db_models.rag_provider_models import (
    DatabaseRagProviderConfiguration,
    DatabaseRagSearchSettingConfiguration,
    DatabaseRagSearchSettingConfigurationVersion,
)
from repositories.rag_experiment_repository import RagExperimentRepository
from schemas.rag_experiment_schemas import (
    RagConfig,
    RagConfigResponse,
    RagExperimentListResponse,
)
from schemas.rag_notebook_schemas import (
    CreateRagNotebookRequest,
    RagNotebook,
    RagNotebookDetail,
    RagNotebookListResponse,
    RagNotebookState,
    RagNotebookStateResponse,
    SetRagNotebookStateRequest,
    UpdateRagNotebookRequest,
)

RagConfigAdapter = TypeAdapter(RagConfig)
RagConfigResponseAdapter = TypeAdapter(RagConfigResponse)

logger = logging.getLogger(__name__)


class RagNotebookRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.experiment_repo = RagExperimentRepository(db_session)

    def _get_db_notebook(self, notebook_id: str) -> DatabaseRagNotebook:
        """Get database RAG notebook by ID or raise 404"""
        db_notebook = (
            self.db_session.query(DatabaseRagNotebook)
            .filter(DatabaseRagNotebook.id == notebook_id)
            .first()
        )
        if not db_notebook:
            raise HTTPException(
                status_code=404,
                detail=f"RAG notebook {notebook_id} not found.",
            )
        return db_notebook

    def _validate_notebook_state(
        self,
        task_id: str,
        state: RagNotebookState | None,
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

        # Validate RAG configs if provided
        if state.rag_configs:
            for config in state.rag_configs:
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
                        raise HTTPException(
                            status_code=400,
                            detail=f"RAG setting configuration '{config.setting_configuration_id}' not found for task {task_id}",
                        )

                    # Validate RAG setting configuration version exists
                    setting_version = (
                        self.db_session.query(
                            DatabaseRagSearchSettingConfigurationVersion,
                        )
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
                        raise HTTPException(
                            status_code=400,
                            detail=f"RAG setting configuration version {config.version} not found for setting configuration {config.setting_configuration_id}",
                        )

                elif config.type == "unsaved":
                    # Validate RAG provider exists
                    rag_provider = (
                        self.db_session.query(DatabaseRagProviderConfiguration)
                        .filter(
                            DatabaseRagProviderConfiguration.task_id == task_id,
                            DatabaseRagProviderConfiguration.id
                            == config.rag_provider_id,
                        )
                        .first()
                    )
                    if not rag_provider:
                        raise HTTPException(
                            status_code=400,
                            detail=f"RAG provider '{config.rag_provider_id}' not found for task {task_id}",
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

    def create_notebook(
        self,
        task_id: str,
        request: CreateRagNotebookRequest,
    ) -> RagNotebookDetail:
        """Create a new RAG notebook with optional initial state"""
        # Validate state resources exist
        self._validate_notebook_state(task_id, request.state)

        # Generate notebook ID
        notebook_id = str(uuid4())

        # Create internal notebook from request
        notebook = RagNotebook._from_request_model(task_id, notebook_id, request)

        # Convert to database model and save
        db_notebook = notebook._to_database_model()
        self.db_session.add(db_notebook)
        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Created RAG notebook {notebook_id} for task {task_id}")

        # Re-fetch with joinedload for dataset relationship
        db_notebook = self._get_db_notebook(notebook_id)
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook_with_experiments = RagNotebook._from_database_model(
            db_notebook,
            [],
            dataset_name,
        )
        return notebook_with_experiments._to_detail_response()

    def get_notebook(self, notebook_id: str) -> RagNotebookDetail:
        """Get RAG notebook by ID"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Get experiments and convert to summaries
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]

        # Convert to internal model and return detail response
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = RagNotebook._from_database_model(
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
    ) -> RagNotebookListResponse:
        """List RAG notebooks for a task with pagination and optional name filter"""
        # Base query with joinedload for experiments to avoid N+1
        query = (
            self.db_session.query(DatabaseRagNotebook)
            .options(joinedload(DatabaseRagNotebook.experiments))
            .filter(DatabaseRagNotebook.task_id == task_id)
        )

        # Apply name filter if provided (exact match)
        if name_filter is not None:
            query = query.filter(DatabaseRagNotebook.name == name_filter)

        # Get total count
        total_count = query.count()

        # Apply sorting
        if pagination_params.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseRagNotebook.created_at))
        else:
            query = query.order_by(desc(DatabaseRagNotebook.created_at))

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
            notebook = RagNotebook._from_database_model(db_notebook, [], None)
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

        return RagNotebookListResponse(
            data=notebooks,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )

    def update_notebook(
        self,
        notebook_id: str,
        request: UpdateRagNotebookRequest,
    ) -> RagNotebookDetail:
        """Update RAG notebook name or description"""
        db_notebook = self._get_db_notebook(notebook_id)

        if request.name is not None:
            db_notebook.name = request.name

        if request.description is not None:
            db_notebook.description = request.description

        db_notebook.updated_at = datetime.now()

        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Updated RAG notebook {notebook_id}")

        # Get experiments and return detail response
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = RagNotebook._from_database_model(
            db_notebook,
            experiments,
            dataset_name,
        )
        return notebook._to_detail_response()

    def set_notebook_state(
        self,
        notebook_id: str,
        request: SetRagNotebookStateRequest,
    ) -> RagNotebookDetail:
        """Set the RAG notebook state"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Validate state resources exist
        self._validate_notebook_state(db_notebook.task_id, request.state)

        # Update state fields
        if request.state.rag_configs is not None:
            db_notebook.rag_configs = [
                config.model_dump(mode="json") for config in request.state.rag_configs
            ]
        else:
            db_notebook.rag_configs = None

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
                eval_ref.model_dump() for eval_ref in request.state.eval_list
            ]
        else:
            db_notebook.eval_configs = None

        db_notebook.updated_at = datetime.now()

        self.db_session.commit()
        self.db_session.refresh(db_notebook)

        logger.info(f"Set state for RAG notebook {notebook_id}")

        # Re-fetch with joinedload for updated dataset relationship
        db_notebook = self._get_db_notebook(notebook_id)
        experiments = [
            self.experiment_repo._db_experiment_to_summary(exp)
            for exp in db_notebook.experiments
        ]
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = RagNotebook._from_database_model(
            db_notebook,
            experiments,
            dataset_name,
        )
        return notebook._to_detail_response()

    def get_notebook_state(self, notebook_id: str) -> RagNotebookStateResponse:
        """Get the current state of a RAG notebook"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Convert to internal model and return state response
        dataset_name = db_notebook.dataset.name if db_notebook.dataset else None
        notebook = RagNotebook._from_database_model(db_notebook, [], dataset_name)
        return notebook._to_state_response()

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete a RAG notebook (experiments are kept with notebook_id=NULL)"""
        db_notebook = self._get_db_notebook(notebook_id)

        self.db_session.delete(db_notebook)
        self.db_session.commit()

        logger.info(f"Deleted RAG notebook {notebook_id}")

    def get_notebook_history(
        self,
        notebook_id: str,
        pagination_params: PaginationParameters,
    ) -> RagExperimentListResponse:
        """Get paginated history of experiments run from this RAG notebook"""
        db_notebook = self._get_db_notebook(notebook_id)

        # Base query for experiments linked to this notebook
        query = self.db_session.query(DatabaseRagExperiment).filter(
            DatabaseRagExperiment.notebook_id == notebook_id,
        )

        # Get total count
        total_count = query.count()

        # Apply sorting (most recent first)
        if pagination_params.sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseRagExperiment.created_at))
        else:
            query = query.order_by(desc(DatabaseRagExperiment.created_at))

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

        return RagExperimentListResponse(
            data=experiments,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )
