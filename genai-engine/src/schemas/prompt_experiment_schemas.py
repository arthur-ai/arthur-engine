from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from arthur_common.models.llm_model_providers import ModelProvider
from litellm.types.utils import ChatCompletionMessageToolCall
from pydantic import BaseModel, Discriminator, Field, model_validator

from schemas.base_experiment_schemas import (
    BaseConfigResult,
    BaseCreateExperimentRequest,
    BaseExperimentDetail,
    BaseExperimentSummary,
    BaseResult,
    BaseTestCase,
    DatasetColumnVariableSource,
    EvalResultSummary,
    InputVariable,
)
from schemas.common_schemas import BasePaginationResponse


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


class PromptRef(BaseModel):
    """Reference to a prompt configuration"""

    name: str = Field(description="Name of the prompt")
    version_list: list[int] = Field(
        description="List of prompt versions to test in the experiment",
    )
    variable_mapping: list[PromptVariableMapping] = Field(
        description="Mapping of prompt variables to dataset columns",
    )


# Prompt Experiment schemas
class PromptExperimentSummary(BaseExperimentSummary):
    """Summary of a prompt experiment"""

    prompt_configs: List[PromptConfig] = Field(
        description="List of prompts being tested",
    )


class CreatePromptExperimentRequest(BaseCreateExperimentRequest):
    """Request to create a new prompt experiment"""

    prompt_configs: List[PromptConfig] = Field(
        description="List of prompt configurations (saved or unsaved)",
    )
    prompt_variable_mapping: list[PromptVariableMapping] = Field(
        description="Shared variable mapping for all prompts",
    )


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


class PromptExperimentDetail(BaseExperimentDetail):
    """Detailed information about a prompt experiment"""

    prompt_configs: List[PromptConfig] = Field(
        description="List of prompts being tested",
    )
    prompt_variable_mapping: list[PromptVariableMapping] = Field(
        description="Shared variable mapping for all prompts",
    )
    summary_results: SummaryResults = Field(
        description="Summary of results across all test cases",
    )


# Pagination schemas
class PromptExperimentListResponse(BasePaginationResponse):
    """Paginated list of prompt experiments"""

    data: list[PromptExperimentSummary] = Field(
        description="List of prompt experiment summaries",
    )


# Test case / result schemas
class PromptOutput(BaseModel):
    """Output from a prompt execution"""

    content: str = Field(description="Content of the prompt response")
    tool_calls: list[ChatCompletionMessageToolCall] = Field(
        default_factory=list,
        description="Tool calls made by the prompt",
    )
    cost: str = Field(description="Cost of the prompt execution")


class PromptResult(BaseResult):
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


class TestCase(BaseTestCase):
    """Individual test case result"""

    prompt_input_variables: list[InputVariable] = Field(
        description="Input variables for the prompt",
    )
    prompt_results: list[PromptResult] = Field(
        description="Results for each prompt version tested",
    )


class TestCaseListResponse(BasePaginationResponse):
    """Paginated list of test cases"""

    data: list[TestCase] = Field(description="List of test cases")


class PromptVersionResult(BaseConfigResult):
    """Result for a specific prompt version within a test case"""

    prompt_input_variables: list[InputVariable] = Field(
        description="Input variables for the prompt",
    )
    rendered_prompt: str = Field(description="Prompt with variables replaced")
    output: Optional[PromptOutput] = Field(
        default=None,
        description="Output from the prompt (None if not yet executed)",
    )


class PromptVersionResultListResponse(BasePaginationResponse):
    """Paginated list of results for a specific prompt version"""

    data: list[PromptVersionResult] = Field(
        description="List of results for the prompt version",
    )
