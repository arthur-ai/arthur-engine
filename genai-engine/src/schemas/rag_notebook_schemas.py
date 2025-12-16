import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, TypeAdapter

from db_models.rag_notebook_models import DatabaseRagNotebook
from schemas.base_experiment_schemas import (
    DatasetRef,
    DatasetRefInput,
    EvalRef,
    ExperimentStatus,
)
from schemas.common_schemas import (
    BasePaginationResponse,
    NewDatasetVersionRowColumnItemRequest,
)
from schemas.rag_experiment_schemas import (
    RagConfig,
    RagConfigResponse,
    RagExperimentSummary,
    SavedRagConfig,
)

# TypeAdapter for RagConfig: RagConfig is a type alias (Annotated[Union[...], Discriminator(...)])
# not a BaseModel, so it doesn't have model_validate(). TypeAdapter allows us to validate
# discriminated union types that aren't Pydantic models.
RagConfigAdapter = TypeAdapter(RagConfig)
RagConfigResponseAdapter = TypeAdapter(RagConfigResponse)


class RagNotebookState(BaseModel):
    """
    Draft state of a RAG notebook - mirrors RAG experiment config but all fields optional.
    Used for requests (input).
    """

    rag_configs: Optional[List[RagConfig]] = Field(
        default=None,
        description="List of RAG configurations",
    )
    dataset_ref: Optional[DatasetRefInput] = Field(
        default=None,
        description="Dataset reference (includes name)",
    )
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]] = Field(
        default=None,
        description="Optional list of column name and value filters. "
        "Only rows matching ALL specified column name-value pairs (AND condition) will be included.",
    )
    eval_list: Optional[List[EvalRef]] = Field(
        default=None,
        description="List of evaluations",
    )


class RagNotebookStateResponse(BaseModel):
    """
    Draft state of a RAG notebook - mirrors RAG experiment config but all fields optional.
    Used for responses (output).
    """

    rag_configs: Optional[List[RagConfigResponse]] = Field(
        default=None,
        description="List of RAG configurations",
    )
    dataset_ref: Optional[DatasetRef] = Field(
        default=None,
        description="Dataset reference (includes name)",
    )
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]] = Field(
        default=None,
        description="Optional list of column name and value filters. "
        "Only rows matching ALL specified column name-value pairs (AND condition) will be included.",
    )
    eval_list: Optional[List[EvalRef]] = Field(
        default=None,
        description="List of evaluations",
    )


class CreateRagNotebookRequest(BaseModel):
    """Request to create a new RAG notebook"""

    name: str = Field(description="Name of the notebook")
    description: Optional[str] = Field(default=None, description="Description")
    state: Optional[RagNotebookState] = Field(default=None, description="Initial state")


class UpdateRagNotebookRequest(BaseModel):
    """Request to update a RAG notebook"""

    name: Optional[str] = Field(default=None, description="New name")
    description: Optional[str] = Field(default=None, description="New description")


class SetRagNotebookStateRequest(BaseModel):
    """Request to set the RAG notebook state"""

    state: RagNotebookState = Field(description="New state for the notebook")


class RagNotebookSummary(BaseModel):
    """Summary of a RAG notebook"""

    id: str = Field(description="Notebook ID")
    task_id: str = Field(description="Associated task ID")
    name: str = Field(description="Notebook name")
    description: Optional[str] = Field(default=None, description="Description")
    created_at: str = Field(description="ISO timestamp when created")
    updated_at: str = Field(description="ISO timestamp when last updated")
    run_count: int = Field(description="Number of experiments run from this notebook")
    latest_run_id: Optional[str] = Field(
        default=None,
        description="ID of most recent experiment run",
    )
    latest_run_status: Optional[ExperimentStatus] = Field(
        default=None,
        description="Status of most recent experiment",
    )


class RagNotebookDetail(BaseModel):
    """Detailed RAG notebook information"""

    id: str = Field(description="Notebook ID")
    task_id: str = Field(description="Associated task ID")
    name: str = Field(description="Notebook name")
    description: Optional[str] = Field(default=None, description="Description")
    created_at: str = Field(description="ISO timestamp when created")
    updated_at: str = Field(description="ISO timestamp when last updated")
    state: RagNotebookStateResponse = Field(description="Current draft state")
    experiments: List[RagExperimentSummary] = Field(
        description="History of experiments run from this notebook",
    )


class RagNotebookListResponse(BasePaginationResponse):
    """Paginated list of RAG notebooks"""

    data: List[RagNotebookSummary] = Field(description="List of notebook summaries")


# Internal Schema for translation between database and response models
class RagNotebook(BaseModel):
    """
    Internal representation of a RAG notebook.
    Handles translation between database models and request/response schemas.
    """

    id: str
    task_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    rag_configs: Optional[List[Dict[str, Any]]]
    dataset_id: Optional[uuid.UUID]
    dataset_name: Optional[str]
    dataset_version: Optional[int]
    dataset_row_filter: Optional[List[Dict[str, Any]]]
    eval_configs: Optional[List[Dict[str, Any]]]
    experiments: List[RagExperimentSummary] = Field(default_factory=list)

    @staticmethod
    def _from_request_model(
        task_id: str,
        notebook_id: str,
        request: CreateRagNotebookRequest,
    ) -> "RagNotebook":
        """Create internal RagNotebook from CreateRagNotebookRequest"""
        # Prepare state JSON
        rag_configs = None
        dataset_id = None
        dataset_version = None
        dataset_row_filter = None
        eval_configs = None

        if request.state:
            if request.state.rag_configs:
                rag_configs = [
                    config.model_dump(mode="json")
                    for config in request.state.rag_configs
                ]

            if request.state.dataset_ref:
                dataset_id = request.state.dataset_ref.id
                dataset_version = request.state.dataset_ref.version

            if request.state.dataset_row_filter:
                dataset_row_filter = [
                    filter_item.model_dump(mode="json")
                    for filter_item in request.state.dataset_row_filter
                ]

            if request.state.eval_list:
                eval_configs = [
                    eval_ref.model_dump(mode="json")
                    for eval_ref in request.state.eval_list
                ]

        return RagNotebook(
            id=notebook_id,
            task_id=task_id,
            name=request.name,
            description=request.description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            rag_configs=rag_configs,
            dataset_id=dataset_id,
            dataset_name=None,  # Will be populated from database lookup
            dataset_version=dataset_version,
            dataset_row_filter=dataset_row_filter,
            eval_configs=eval_configs,
        )

    @staticmethod
    def _from_database_model(
        db_notebook: DatabaseRagNotebook,
        experiments: List[RagExperimentSummary],
        dataset_name: Optional[str] = None,
    ) -> "RagNotebook":
        """Create internal RagNotebook from DatabaseRagNotebook"""
        return RagNotebook(
            id=db_notebook.id,
            task_id=db_notebook.task_id,
            name=db_notebook.name,
            description=db_notebook.description,
            created_at=db_notebook.created_at,
            updated_at=db_notebook.updated_at,
            rag_configs=db_notebook.rag_configs,
            dataset_id=db_notebook.dataset_id,
            dataset_name=dataset_name,
            dataset_version=db_notebook.dataset_version,
            dataset_row_filter=db_notebook.dataset_row_filter,
            eval_configs=db_notebook.eval_configs,
            experiments=experiments,
        )

    def _to_database_model(self) -> DatabaseRagNotebook:
        """Convert internal RagNotebook to DatabaseRagNotebook"""
        return DatabaseRagNotebook(
            id=self.id,
            task_id=self.task_id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            updated_at=self.updated_at,
            rag_configs=self.rag_configs,
            dataset_id=self.dataset_id,
            dataset_version=self.dataset_version,
            dataset_row_filter=self.dataset_row_filter,
            eval_configs=self.eval_configs,
        )

    def _to_summary_response(
        self,
        run_count: int,
        latest_run_id: Optional[str],
        latest_run_status: Optional[ExperimentStatus],
    ) -> RagNotebookSummary:
        """Convert internal RagNotebook to RagNotebookSummary response"""
        return RagNotebookSummary(
            id=self.id,
            task_id=self.task_id,
            name=self.name,
            description=self.description,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
            run_count=run_count,
            latest_run_id=latest_run_id,
            latest_run_status=latest_run_status,
        )

    def _to_detail_response(self) -> RagNotebookDetail:
        """Convert internal RagNotebook to RagNotebookDetail response"""
        # Convert state from JSON to Pydantic models (request types first)
        state_request = RagNotebookState()

        if self.rag_configs is not None:
            state_request.rag_configs = [
                RagConfigAdapter.validate_python(config) for config in self.rag_configs
            ]

        if (
            self.dataset_id is not None
            and self.dataset_version is not None
            and self.dataset_name is not None
        ):
            state_request.dataset_ref = DatasetRef(
                id=self.dataset_id,
                name=self.dataset_name,
                version=self.dataset_version,
            )

        if self.dataset_row_filter is not None:
            state_request.dataset_row_filter = [
                NewDatasetVersionRowColumnItemRequest.model_validate(filter_item)
                for filter_item in self.dataset_row_filter
            ]

        if self.eval_configs is not None:
            state_request.eval_list = [
                EvalRef.model_validate(eval_config) for eval_config in self.eval_configs
            ]

        # Convert to response state (with response types)
        state = RagNotebookStateResponse()
        if state_request.rag_configs is not None:
            state.rag_configs = [
                SavedRagConfig.to_response(config)
                for config in state_request.rag_configs
            ]
        state.dataset_ref = state_request.dataset_ref
        state.dataset_row_filter = state_request.dataset_row_filter
        state.eval_list = state_request.eval_list

        return RagNotebookDetail(
            id=self.id,
            task_id=self.task_id,
            name=self.name,
            description=self.description,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
            state=state,
            experiments=self.experiments,
        )

    def _to_state_response(self) -> RagNotebookStateResponse:
        """Convert internal RagNotebook to RagNotebookStateResponse"""
        # Convert state from JSON to Pydantic models (request types first)
        state_request = RagNotebookState()

        if self.rag_configs is not None:
            state_request.rag_configs = [
                RagConfigAdapter.validate_python(config) for config in self.rag_configs
            ]

        if (
            self.dataset_id is not None
            and self.dataset_version is not None
            and self.dataset_name is not None
        ):
            state_request.dataset_ref = DatasetRef(
                id=self.dataset_id,
                name=self.dataset_name,
                version=self.dataset_version,
            )

        if self.dataset_row_filter is not None:
            state_request.dataset_row_filter = [
                NewDatasetVersionRowColumnItemRequest.model_validate(filter_item)
                for filter_item in self.dataset_row_filter
            ]

        if self.eval_configs is not None:
            state_request.eval_list = [
                EvalRef.model_validate(eval_config) for eval_config in self.eval_configs
            ]

        # Convert to response state (with response types)
        state = RagNotebookStateResponse()
        if state_request.rag_configs is not None:
            state.rag_configs = [
                SavedRagConfig.to_response(config)
                for config in state_request.rag_configs
            ]
        state.dataset_ref = state_request.dataset_ref
        state.dataset_row_filter = state_request.dataset_row_filter
        state.eval_list = state_request.eval_list

        return state
