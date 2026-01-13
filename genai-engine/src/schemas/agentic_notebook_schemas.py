from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.agentic_experiment_schemas import (
    AgenticEvalRef,
    AgenticExperimentSummary,
    HttpTemplate,
    TemplateVariableMapping,
)
from schemas.base_experiment_schemas import (
    DatasetRef,
    DatasetRefInput,
    ExperimentStatus,
)
from schemas.common_schemas import (
    BasePaginationResponse,
    NewDatasetVersionRowColumnItemRequest,
)


class AgenticNotebookState(BaseModel):
    """
    Draft state of an agentic notebook - mirrors agentic experiment config but all fields optional.
    Used for requests (input).
    """

    http_template: Optional[HttpTemplate] = Field(
        default=None,
        description="HTTP template configuration for the agent endpoint",
    )
    template_variable_mapping: Optional[List[TemplateVariableMapping]] = Field(
        default=None,
        description="Mapping of template variables to their sources (dataset columns, request-time parameters, or generated variables like UUIDs)",
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
    eval_list: Optional[List[AgenticEvalRef]] = Field(
        default=None,
        description="List of evaluations",
    )


class AgenticNotebookStateResponse(BaseModel):
    """
    Draft state of an agentic notebook - mirrors agentic experiment config but all fields optional.
    Used for responses (output).
    """

    http_template: Optional[HttpTemplate] = Field(
        default=None,
        description="HTTP template configuration for the agent endpoint",
    )
    template_variable_mapping: Optional[List[TemplateVariableMapping]] = Field(
        default=None,
        description="Mapping of template variables to their sources (dataset columns, request-time parameters, or generated variables like UUIDs)",
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
    eval_list: Optional[List[AgenticEvalRef]] = Field(
        default=None,
        description="List of evaluations",
    )


class CreateAgenticNotebookRequest(BaseModel):
    """Request to create a new agentic notebook"""

    name: str = Field(description="Name of the notebook")
    description: Optional[str] = Field(default=None, description="Description")
    state: Optional[AgenticNotebookState] = Field(
        default=None,
        description="Initial state",
    )


class UpdateAgenticNotebookRequest(BaseModel):
    """Request to update an agentic notebook"""

    name: Optional[str] = Field(default=None, description="New name")
    description: Optional[str] = Field(default=None, description="New description")


class SetAgenticNotebookStateRequest(BaseModel):
    """Request to set the agentic notebook state"""

    state: AgenticNotebookState = Field(description="New state for the notebook")


class AgenticNotebookSummary(BaseModel):
    """Summary of an agentic notebook"""

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


class AgenticNotebookDetail(BaseModel):
    """Detailed agentic notebook information"""

    id: str = Field(description="Notebook ID")
    task_id: str = Field(description="Associated task ID")
    name: str = Field(description="Notebook name")
    description: Optional[str] = Field(default=None, description="Description")
    created_at: str = Field(description="ISO timestamp when created")
    updated_at: str = Field(description="ISO timestamp when last updated")
    state: AgenticNotebookStateResponse = Field(description="Current draft state")
    experiments: List[AgenticExperimentSummary] = Field(
        description="History of experiments run from this notebook",
    )


class AgenticNotebookListResponse(BasePaginationResponse):
    """Paginated list of agentic notebooks"""

    data: List[AgenticNotebookSummary] = Field(description="List of notebook summaries")
