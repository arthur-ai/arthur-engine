from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from db_models.notebook_models import DatabaseNotebook
from schemas.prompt_experiment_schemas import (
    DatasetRef,
    EvalRef,
    ExperimentStatus,
    PromptConfig,
    PromptExperimentSummary,
    PromptVariableMapping,
    SavedPromptConfig,
    UnsavedPromptConfig,
)


class NotebookState(BaseModel):
    """
    Draft state of a notebook - mirrors experiment config but all fields optional.
    """

    prompt_configs: Optional[List[PromptConfig]] = Field(
        default=None, description="List of prompt configurations"
    )
    prompt_variable_mapping: Optional[List[PromptVariableMapping]] = Field(
        default=None, description="Variable mappings for prompts"
    )
    dataset_ref: Optional[DatasetRef] = Field(
        default=None, description="Dataset reference"
    )
    eval_list: Optional[List[EvalRef]] = Field(
        default=None, description="List of evaluations"
    )


class CreateNotebookRequest(BaseModel):
    """Request to create a new notebook"""

    name: str = Field(description="Name of the notebook")
    description: Optional[str] = Field(default=None, description="Description")
    state: Optional[NotebookState] = Field(
        default=None, description="Initial state"
    )


class UpdateNotebookRequest(BaseModel):
    """Request to update a notebook"""

    name: Optional[str] = Field(default=None, description="New name")
    description: Optional[str] = Field(default=None, description="New description")


class SetNotebookStateRequest(BaseModel):
    """Request to set the notebook state"""

    state: NotebookState = Field(description="New state for the notebook")


class NotebookSummary(BaseModel):
    """Summary of a notebook"""

    id: str = Field(description="Notebook ID")
    task_id: str = Field(description="Associated task ID")
    name: str = Field(description="Notebook name")
    description: Optional[str] = Field(default=None, description="Description")
    created_at: str = Field(description="ISO timestamp when created")
    updated_at: str = Field(description="ISO timestamp when last updated")
    run_count: int = Field(description="Number of experiments run from this notebook")
    latest_run_id: Optional[str] = Field(
        default=None, description="ID of most recent experiment run"
    )
    latest_run_status: Optional[ExperimentStatus] = Field(
        default=None, description="Status of most recent experiment"
    )


class NotebookDetail(BaseModel):
    """Detailed notebook information"""

    id: str = Field(description="Notebook ID")
    task_id: str = Field(description="Associated task ID")
    name: str = Field(description="Notebook name")
    description: Optional[str] = Field(default=None, description="Description")
    created_at: str = Field(description="ISO timestamp when created")
    updated_at: str = Field(description="ISO timestamp when last updated")
    state: NotebookState = Field(description="Current draft state")
    experiments: List[PromptExperimentSummary] = Field(
        description="History of experiments run from this notebook"
    )


class RunNotebookRequest(BaseModel):
    """Request to run a notebook as an experiment"""

    experiment_name: Optional[str] = Field(
        default=None,
        description="Name for the experiment (defaults to notebook name + run number)",
    )
    experiment_description: Optional[str] = Field(
        default=None, description="Description for the experiment"
    )


class NotebookValidationResponse(BaseModel):
    """Response from validating notebook state"""

    valid: bool = Field(description="Whether the notebook state is valid and complete")
    errors: List[str] = Field(
        description="List of validation errors (empty if valid)"
    )


class NotebookListResponse(BaseModel):
    """Paginated list of notebooks"""

    data: List[NotebookSummary] = Field(description="List of notebook summaries")
    page: int = Field(description="Current page number (0-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    total_count: int = Field(description="Total number of notebooks")


# Internal Schema for translation between database and response models
class Notebook(BaseModel):
    """
    Internal representation of a notebook.
    Handles translation between database models and request/response schemas.
    """

    id: str
    task_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    prompt_configs: Optional[List[Dict[str, Any]]]
    prompt_variable_mapping: Optional[List[Dict[str, Any]]]
    dataset_id: Optional[str]
    dataset_version: Optional[int]
    eval_configs: Optional[List[Dict[str, Any]]]
    experiments: List[PromptExperimentSummary] = Field(default_factory=list)

    @staticmethod
    def _from_request_model(
        task_id: str, notebook_id: str, request: CreateNotebookRequest
    ) -> "Notebook":
        """Create internal Notebook from CreateNotebookRequest"""
        # Prepare state JSON
        prompt_configs = None
        prompt_variable_mapping = None
        dataset_id = None
        dataset_version = None
        eval_configs = None

        if request.state:
            if request.state.prompt_configs:
                prompt_configs = [
                    config.model_dump() for config in request.state.prompt_configs
                ]

            if request.state.prompt_variable_mapping:
                prompt_variable_mapping = [
                    mapping.model_dump()
                    for mapping in request.state.prompt_variable_mapping
                ]

            if request.state.dataset_ref:
                dataset_id = str(request.state.dataset_ref.id)
                dataset_version = request.state.dataset_ref.version

            if request.state.eval_list:
                eval_configs = [
                    eval_ref.model_dump() for eval_ref in request.state.eval_list
                ]

        return Notebook(
            id=notebook_id,
            task_id=task_id,
            name=request.name,
            description=request.description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            prompt_configs=prompt_configs,
            prompt_variable_mapping=prompt_variable_mapping,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            eval_configs=eval_configs,
        )

    @staticmethod
    def _from_database_model(
        db_notebook: DatabaseNotebook, experiments: List[PromptExperimentSummary]
    ) -> "Notebook":
        """Create internal Notebook from DatabaseNotebook"""
        return Notebook(
            id=db_notebook.id,
            task_id=db_notebook.task_id,
            name=db_notebook.name,
            description=db_notebook.description,
            created_at=db_notebook.created_at,
            updated_at=db_notebook.updated_at,
            prompt_configs=db_notebook.prompt_configs,
            prompt_variable_mapping=db_notebook.prompt_variable_mapping,
            dataset_id=db_notebook.dataset_id,
            dataset_version=db_notebook.dataset_version,
            eval_configs=db_notebook.eval_configs,
            experiments=experiments,
        )

    def _to_database_model(self) -> DatabaseNotebook:
        """Convert internal Notebook to DatabaseNotebook"""
        return DatabaseNotebook(
            id=self.id,
            task_id=self.task_id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            updated_at=self.updated_at,
            prompt_configs=self.prompt_configs,
            prompt_variable_mapping=self.prompt_variable_mapping,
            dataset_id=self.dataset_id,
            dataset_version=self.dataset_version,
            eval_configs=self.eval_configs,
        )

    def _to_summary_response(
        self, run_count: int, latest_run_id: Optional[str], latest_run_status: Optional[ExperimentStatus]
    ) -> NotebookSummary:
        """Convert internal Notebook to NotebookSummary response"""
        return NotebookSummary(
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

    def _to_detail_response(self) -> NotebookDetail:
        """Convert internal Notebook to NotebookDetail response"""
        # Convert state from JSON to Pydantic models
        state = NotebookState()

        if self.prompt_configs is not None:
            state.prompt_configs = [
                (
                    SavedPromptConfig.model_validate(config)
                    if config.get("type") == "saved"
                    else UnsavedPromptConfig.model_validate(config)
                )
                for config in self.prompt_configs
            ]

        if self.prompt_variable_mapping is not None:
            state.prompt_variable_mapping = [
                PromptVariableMapping.model_validate(mapping)
                for mapping in self.prompt_variable_mapping
            ]

        if self.dataset_id is not None and self.dataset_version is not None:
            state.dataset_ref = DatasetRef(
                id=self.dataset_id,
                version=self.dataset_version,
            )

        if self.eval_configs is not None:
            state.eval_list = [
                EvalRef.model_validate(eval_config) for eval_config in self.eval_configs
            ]

        return NotebookDetail(
            id=self.id,
            task_id=self.task_id,
            name=self.name,
            description=self.description,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
            state=state,
            experiments=self.experiments,
        )

    def _to_state_response(self) -> NotebookState:
        """Convert internal Notebook to NotebookState response"""
        state = NotebookState()

        if self.prompt_configs is not None:
            state.prompt_configs = [
                (
                    SavedPromptConfig.model_validate(config)
                    if config.get("type") == "saved"
                    else UnsavedPromptConfig.model_validate(config)
                )
                for config in self.prompt_configs
            ]

        if self.prompt_variable_mapping is not None:
            state.prompt_variable_mapping = [
                PromptVariableMapping.model_validate(mapping)
                for mapping in self.prompt_variable_mapping
            ]

        if self.dataset_id is not None and self.dataset_version is not None:
            state.dataset_ref = DatasetRef(
                id=self.dataset_id,
                version=self.dataset_version,
            )

        if self.eval_configs is not None:
            state.eval_list = [
                EvalRef.model_validate(eval_config) for eval_config in self.eval_configs
            ]

        return state
