from typing import List, Optional

from pydantic import BaseModel, Field, TypeAdapter

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
