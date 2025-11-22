from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Discriminator, Field, model_validator

from schemas.common_schemas import NewDatasetVersionRowColumnItemRequest
from schemas.enums import ModelProvider


class ExperimentStatus(str, Enum):
    """Status of a prompt experiment"""

    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class TestCaseStatus(str, Enum):
    """Status of a test case"""

    QUEUED = "queued"
    RUNNING = "running"
    EVALUATING = "evaluating"
    FAILED = "failed"
    COMPLETED = "completed"


# Variable mapping schemas
class DatasetColumnSource(BaseModel):
    """Reference to a dataset column"""

    name: str = Field(description="Name of the dataset column")


class ExperimentOutputSource(BaseModel):
    """Reference to experiment output"""

    json_path: Optional[str] = Field(
        default=None,
        description="Optional JSON path to extract from experiment output",
    )


class DatasetColumnVariableSource(BaseModel):
    """Variable source from a dataset column"""

    type: Literal["dataset_column"] = Field(
        description="Type of source: 'dataset_column'",
    )
    dataset_column: DatasetColumnSource = Field(description="Dataset column source")


class ExperimentOutputVariableSource(BaseModel):
    """Variable source from experiment output"""

    type: Literal["experiment_output"] = Field(
        description="Type of source: 'experiment_output'",
    )
    experiment_output: ExperimentOutputSource = Field(
        description="Experiment output source",
    )


# Union type with discriminator (used for eval mappings)
VariableSource = Annotated[
    Union[DatasetColumnVariableSource, ExperimentOutputVariableSource],
    Discriminator("type"),
]


class PromptVariableMapping(BaseModel):
    """Mapping of a prompt variable to a dataset column source"""

    variable_name: str = Field(description="Name of the prompt variable")
    source: DatasetColumnVariableSource = Field(description="Dataset column source")


class SavedPromptConfig(BaseModel):
    """Configuration for a saved prompt"""

    type: Literal["saved"] = "saved"
    name: str = Field(description="Name of the saved prompt")
    version: int = Field(description="Version of the saved prompt")


class UnsavedPromptConfig(BaseModel):
    """Configuration for an unsaved prompt"""

    type: Literal["unsaved"] = "unsaved"
    auto_name: Optional[str] = Field(
        default=None,
        description="Auto-generated name (set by backend)",
    )
    messages: List[Dict[str, Any]] = Field(description="Prompt messages")
    model_name: str = Field(description="LLM model name")
    model_provider: ModelProvider = Field(description="LLM provider")
    tools: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Available tools",
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="LLM config settings",
    )
    variables: Optional[List[str]] = Field(
        default=None,
        description="Variables (auto-detected if not provided)",
    )


PromptConfig = Annotated[
    Union[SavedPromptConfig, UnsavedPromptConfig],
    Discriminator("type"),
]


class EvalVariableMapping(BaseModel):
    """Mapping of an eval variable to its source (dataset column or experiment output)"""

    variable_name: str = Field(description="Name of the eval variable")
    source: VariableSource = Field(description="Source of the variable value")


# Reference schemas
class DatasetRef(BaseModel):
    """Reference to a dataset and version"""

    id: UUID = Field(description="Dataset ID")
    version: int = Field(description="Dataset version number")


class PromptRef(BaseModel):
    """Reference to a prompt configuration"""

    name: str = Field(description="Name of the prompt")
    version_list: list[int] = Field(
        description="List of prompt versions to test in the experiment",
    )
    variable_mapping: list[PromptVariableMapping] = Field(
        description="Mapping of prompt variables to dataset columns",
    )


class EvalRef(BaseModel):
    """Reference to an evaluation configuration"""

    name: str = Field(description="Name of the evaluation")
    version: int = Field(description="Version of the evaluation")
    variable_mapping: list[EvalVariableMapping] = Field(
        description="Mapping of eval variables to data sources",
    )


# Prompt Experiment schemas
class PromptExperimentSummary(BaseModel):
    """Summary of a prompt experiment"""

    id: str = Field(description="Unique identifier for the experiment")
    name: str = Field(description="Name of the experiment")
    description: Optional[str] = Field(
        default=None,
        description="Description of the experiment",
    )
    created_at: str = Field(description="ISO timestamp when experiment was created")
    finished_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when experiment finished",
    )
    status: ExperimentStatus = Field(description="Current status of the experiment")
    prompt_configs: List[PromptConfig] = Field(
        description="List of prompts being tested",
    )
    total_rows: int = Field(description="Total number of test rows in the experiment")
    completed_rows: int = Field(
        description="Number of test rows completed successfully",
    )
    failed_rows: int = Field(description="Number of test rows that failed")
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost of running the experiment",
    )


class CreatePromptExperimentRequest(BaseModel):
    """Request to create a new prompt experiment"""

    name: str = Field(description="Name for the experiment")
    description: Optional[str] = Field(
        default=None,
        description="Description of the experiment",
    )
    dataset_ref: DatasetRef = Field(description="Reference to the dataset to use")
    prompt_configs: List[PromptConfig] = Field(
        description="List of prompt configurations (saved or unsaved)",
    )
    prompt_variable_mapping: list[PromptVariableMapping] = Field(
        description="Shared variable mapping for all prompts",
    )
    eval_list: list[EvalRef] = Field(description="List of evaluations to run")
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]] = Field(
        default=None,
        description="Optional list of column name and value filters. "
        "Only rows matching ALL specified column name-value pairs (AND condition) will be included in the experiment. "
        "If not specified, all rows from the dataset will be used.",
    )


class EvalResultSummary(BaseModel):
    """Results for a single eval"""

    eval_name: str = Field(description="Name of the evaluation")
    eval_version: str = Field(description="Version of the evaluation")
    pass_count: int = Field(description="Number of test cases that passed")
    total_count: int = Field(description="Total number of test cases evaluated")


class PromptEvalResultSummaries(BaseModel):
    """Summary of evaluation results for a prompt version"""

    prompt_key: str | None = Field(
        default=None,
        description="Prompt key: 'saved:name:version' or 'unsaved:auto_name'",
    )
    prompt_type: str | None = Field(
        default=None,
        description="Type: 'saved' or 'unsaved'",
    )
    prompt_name: str | None = Field(
        default=None,
        description="Name of the prompt (for saved prompts, or auto_name for unsaved)",
    )
    prompt_version: str | None = Field(
        default=None,
        description="Version of the prompt (for saved prompts only)",
    )
    eval_results: list[EvalResultSummary] = Field(
        description="Results for each evaluation run on this prompt version",
    )

    @model_validator(mode="after")
    def populate_key_and_type(self) -> "PromptEvalResultSummaries":
        """
        Populate prompt_key and prompt_type from prompt_name/version if missing.
        This provides backward compatibility for existing experiments.
        """
        # If we already have prompt_key and prompt_type, nothing to do
        if self.prompt_key and self.prompt_type:
            return self

        # If we have prompt_name and prompt_version, construct key and type
        if self.prompt_name and self.prompt_version:
            self.prompt_key = f"saved:{self.prompt_name}:{self.prompt_version}"
            self.prompt_type = "saved"
        elif self.prompt_name:
            # Fallback for edge cases
            self.prompt_key = f"saved:{self.prompt_name}:1"
            self.prompt_type = "saved"

        return self


class SummaryResults(BaseModel):
    """Summary results across all prompt versions and evaluations"""

    prompt_eval_summaries: list[PromptEvalResultSummaries] = Field(
        description="Summary for each prompt version tested",
    )


class PromptExperimentDetail(BaseModel):
    """Detailed information about a prompt experiment"""

    id: str = Field(description="Unique identifier for the experiment")
    name: str = Field(description="Name of the experiment")
    description: Optional[str] = Field(
        default=None,
        description="Description of the experiment",
    )
    created_at: str = Field(description="ISO timestamp when experiment was created")
    finished_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp when experiment finished",
    )
    status: ExperimentStatus = Field(description="Current status of the experiment")
    prompt_configs: List[PromptConfig] = Field(
        description="List of prompts being tested",
    )
    total_rows: int = Field(description="Total number of test rows in the experiment")
    completed_rows: int = Field(
        description="Number of test rows completed successfully",
    )
    failed_rows: int = Field(description="Number of test rows that failed")
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost of running the experiment",
    )
    dataset_ref: DatasetRef = Field(description="Reference to the dataset used")
    prompt_variable_mapping: list[PromptVariableMapping] = Field(
        description="Shared variable mapping for all prompts",
    )
    eval_list: list[EvalRef] = Field(description="List of evaluations being run")
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]] = Field(
        default=None,
        description="Optional list of column name and value filters applied to dataset rows. "
        "Only rows matching ALL specified column name-value pairs (AND condition) were included in the experiment.",
    )
    summary_results: SummaryResults = Field(
        description="Summary of results across all test cases",
    )
    notebook_id: Optional[str] = Field(
        default=None,
        description="Optional notebook ID this experiment is linked to",
    )


# Pagination schemas
class PromptExperimentListResponse(BaseModel):
    """Paginated list of prompt experiments"""

    data: list[PromptExperimentSummary] = Field(
        description="List of prompt experiment summaries",
    )
    page: int = Field(description="Current page number (0-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    total_count: int = Field(description="Total number of prompt experiments")


# Test case / result schemas
class InputVariable(BaseModel):
    """Input variable for a test case"""

    variable_name: str = Field(description="Name of the variable")
    value: str = Field(description="Value of the variable")


class PromptOutput(BaseModel):
    """Output from a prompt execution"""

    content: str = Field(description="Content of the prompt response")
    tool_calls: list = Field(
        default_factory=list,
        description="Tool calls made by the prompt",
    )
    cost: str = Field(description="Cost of the prompt execution")


class EvalExecutionResult(BaseModel):
    """Results from an eval execution"""

    score: float = Field(description="Score from the evaluation")
    explanation: str = Field(description="Explanation of the score")
    cost: str = Field(description="Cost of the evaluation")


class EvalExecution(BaseModel):
    """Details of an eval execution"""

    eval_name: str = Field(description="Name of the evaluation")
    eval_version: str = Field(description="Version of the evaluation")
    eval_input_variables: list[InputVariable] = Field(
        description="Input variables used for the eval",
    )
    eval_results: Optional[EvalExecutionResult] = Field(
        default=None,
        description="Results from the eval (None if not yet executed)",
    )


class PromptResult(BaseModel):
    """Results from a prompt execution with evals"""

    prompt_key: str = Field(
        description="Prompt key: 'saved:name:version' or 'unsaved:auto_name'",
    )
    prompt_type: str = Field(description="Type: 'saved' or 'unsaved'")
    name: Optional[str] = Field(
        default=None,
        description="Name of the prompt (for saved prompts)",
    )
    version: Optional[str] = Field(
        default=None,
        description="Version of the prompt (for saved prompts)",
    )
    rendered_prompt: str = Field(description="Prompt with variables replaced")
    output: Optional[PromptOutput] = Field(
        default=None,
        description="Output from the prompt (None if not yet executed)",
    )
    evals: list[EvalExecution] = Field(
        description="Evaluation results for this prompt output",
    )


class TestCase(BaseModel):
    """Individual test case result"""

    status: TestCaseStatus = Field(description="Status of the test case")
    dataset_row_id: str = Field(description="ID of the dataset row")
    prompt_input_variables: list[InputVariable] = Field(
        description="Input variables for the prompt",
    )
    prompt_results: list[PromptResult] = Field(
        description="Results for each prompt version tested",
    )
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost for this test case",
    )


class TestCaseListResponse(BaseModel):
    """Paginated list of test cases"""

    data: list[TestCase] = Field(description="List of test cases")
    page: int = Field(description="Current page number (0-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    total_count: int = Field(description="Total number of test cases")


class PromptVersionResult(BaseModel):
    """Result for a specific prompt version within a test case"""

    status: TestCaseStatus = Field(description="Status of the test case")
    dataset_row_id: str = Field(description="ID of the dataset row")
    prompt_input_variables: list[InputVariable] = Field(
        description="Input variables for the prompt",
    )
    rendered_prompt: str = Field(description="Prompt with variables replaced")
    output: Optional[PromptOutput] = Field(
        default=None,
        description="Output from the prompt (None if not yet executed)",
    )
    evals: list[EvalExecution] = Field(
        description="Evaluation results for this prompt output",
    )
    total_cost: Optional[str] = Field(
        default=None,
        description="Total cost for this specific prompt execution",
    )


class PromptVersionResultListResponse(BaseModel):
    """Paginated list of results for a specific prompt version"""

    data: list[PromptVersionResult] = Field(
        description="List of results for the prompt version",
    )
    page: int = Field(description="Current page number (0-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    total_count: int = Field(description="Total number of results")
