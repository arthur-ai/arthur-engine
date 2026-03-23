from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Discriminator, Field, model_validator

from schemas.base_experiment_schemas import (
    BaseConfigResult,
    BaseEvalRef,
    BaseExperimentSummary,
    BaseResult,
    BaseTestCase,
    DatasetColumnVariableSource,
    DatasetRefInput,
    EvalResultSummary,
    GroundBaseExperimentDetail,
    InputVariable,
    TransformVariableExperimentOutputSource,
)
from schemas.common_schemas import (
    BasePaginationResponse,
    NewDatasetVersionRowColumnItemRequest,
)
from schemas.enums import AgenticExperimentGeneratorType


# HTTP Template schemas
class HttpHeader(BaseModel):
    """HTTP header with support for variable placeholders"""

    name: str = Field(description="Header name (supports {{variable}} placeholders)")
    value: str = Field(description="Header value (supports {{variable}} placeholders)")


class HttpTemplate(BaseModel):
    """HTTP template configuration for agent endpoint"""

    endpoint_name: str = Field(description="Name of the endpoint")
    endpoint_url: str = Field(description="URL of the endpoint")
    headers: List[HttpHeader] = Field(
        default_factory=list,
        description="HTTP headers (supports {{variable}} placeholders in names and values)",
    )
    request_body: str = Field(
        description="Request body as a string (supports {{variable}} placeholders)",
    )


# Variable source schemas for template variables
class RequestTimeParameterSource(BaseModel):
    """Variable source from request-time parameters (e.g., tokens, API keys)"""

    type: Literal["request_time_parameter"] = Field(
        description="Type of source: 'request_time_parameter'",
    )


class RequestTimeParameter(BaseModel):
    """Request-time parameter with name and value (e.g., API keys, tokens)"""

    name: str = Field(
        description="Name of the request-time parameter (must match variable_name in template_variable_mapping)",
    )
    value: str = Field(
        description="Value of the request-time parameter (not saved, provided at execution time)",
    )


class GeneratedVariableSource(BaseModel):
    """Variable source for generated values (e.g., UUIDs, timestamps)"""

    model_config = ConfigDict(use_enum_values=True)

    type: Literal["generated"] = Field(
        description="Type of source: 'generated'",
    )
    generator_type: AgenticExperimentGeneratorType = Field(
        description="Type of generator to use. Supported values: 'uuid', 'session_id'. Exactly one session_id is required per experiment.",
    )


# Union type for template variable sources
TemplateVariableSource = Annotated[
    Union[
        DatasetColumnVariableSource,
        RequestTimeParameterSource,
        GeneratedVariableSource,
    ],
    Discriminator("type"),
]


class TemplateVariableMapping(BaseModel):
    """Mapping of a template variable to its source"""

    variable_name: str = Field(description="Name of the template variable")
    source: TemplateVariableSource = Field(description="Source of the variable value")


# Agentic experiment output source - only supports transform variables
# Since there's only one type, we use a type alias (no Union/Discriminator needed)
AgenticExperimentOutputSource = TransformVariableExperimentOutputSource


class AgenticExperimentOutputVariableSource(BaseModel):
    """Variable source from experiment output (agentic experiments only support transform variables)"""

    type: Literal["experiment_output"] = Field(
        description="Type of source: 'experiment_output'",
    )
    experiment_output: AgenticExperimentOutputSource = Field(
        description="Experiment output source (only transform variables supported)",
    )


# Extended variable source union for evals (includes dataset columns and experiment output with transform support)
# Agentic experiments only support transform variables, not JSON path extraction
AgenticEvalVariableSource = Annotated[
    Union[
        DatasetColumnVariableSource,
        AgenticExperimentOutputVariableSource,
    ],
    Discriminator("type"),
]


class AgenticEvalVariableMapping(BaseModel):
    """Mapping of an eval variable to its source (dataset column or experiment output).

    For transform variables, use ExperimentOutputVariableSource with transform_variable_name
    in the experiment_output field. The transform_id comes from the associated AgenticEvalRef.
    """

    variable_name: str = Field(description="Name of the eval variable")
    source: AgenticEvalVariableSource = Field(
        description="Source of the variable value",
    )


# Eval configuration with transform
class AgenticEvalRef(BaseEvalRef):
    """Reference to an evaluation configuration with transform"""

    transform_id: UUID = Field(
        description="ID of the transform to apply to the trace before evaluation",
    )

    # Override variable_mapping to use AgenticEvalVariableMapping instead of EvalVariableMapping
    # This ensures transform variables are used instead of json_path
    variable_mapping: list[AgenticEvalVariableMapping] = Field(
        description="Mapping of eval variables to data sources (supports transform variables for agentic experiments)",
    )


# Agentic Experiment schemas
class AgenticExperimentSummary(BaseExperimentSummary):
    """Summary of an agentic experiment"""

    http_template: HttpTemplate = Field(
        description="HTTP template configuration for the agent endpoint",
    )


class CreateAgenticExperimentRequest(BaseModel):
    """Request to create a new agentic experiment"""

    name: str = Field(description="Name for the experiment")
    description: Optional[str] = Field(
        default=None,
        description="Description of the experiment",
    )
    dataset_ref: DatasetRefInput = Field(description="Reference to the dataset to use")
    dataset_row_filter: Optional[List[NewDatasetVersionRowColumnItemRequest]] = Field(
        default=None,
        description="Optional list of column name and value filters. "
        "Only rows matching ALL specified column name-value pairs (AND condition) will be included in the experiment. "
        "If not specified, all rows from the dataset will be used.",
    )
    http_template: HttpTemplate = Field(
        description="HTTP template configuration for the agent endpoint",
    )
    template_variable_mapping: list[TemplateVariableMapping] = Field(
        description="Mapping of template variables to their sources (dataset columns, request-time parameters, or generated variables like UUIDs)",
    )
    request_time_parameters: Optional[List[RequestTimeParameter]] = Field(
        default=None,
        description="List of request-time parameters (e.g., API keys, tokens). "
        "These are NOT stored in the database for security reasons - they are passed directly to the execution thread.",
    )
    eval_list: list[AgenticEvalRef] = Field(
        description="List of evaluations to run, each with an associated transform",
    )

    @model_validator(mode="after")
    def validate_session_id(self) -> "CreateAgenticExperimentRequest":
        session_id_count = 0
        if self.template_variable_mapping:
            for variable in self.template_variable_mapping:
                if (
                    variable.source.type == "generated"
                    and variable.source.generator_type
                    == AgenticExperimentGeneratorType.SESSION_ID
                ):
                    if session_id_count > 0:
                        raise ValueError(
                            "Exactly one session_id is required per experiment",
                        )
                    session_id_count += 1

        if session_id_count == 0:
            raise ValueError(
                "A session_id variable is required to create an agentic experiment",
            )

        return self


class AgenticEvalResultSummaries(BaseModel):
    """Summary of evaluation results for an agentic experiment"""

    eval_name: str = Field(description="Name of the evaluation")
    eval_version: str = Field(description="Version of the evaluation")
    transform_id: UUID = Field(
        description="ID of the transform used for this evaluation",
    )
    eval_results: list[EvalResultSummary] = Field(
        description="Results for this evaluation",
    )


class AgenticSummaryResults(BaseModel):
    """Summary results across all evaluations"""

    eval_summaries: list[AgenticEvalResultSummaries] = Field(
        description="Summary for each evaluation run",
    )


class AgenticExperimentDetail(GroundBaseExperimentDetail):
    """Detailed information about an agentic experiment"""

    http_template: HttpTemplate = Field(
        description="HTTP template configuration for the agent endpoint",
    )
    template_variable_mapping: list[TemplateVariableMapping] = Field(
        description="Mapping of template variables to their sources (dataset columns, request-time parameters, or generated variables)",
    )
    eval_list: list[AgenticEvalRef] = Field(
        description="List of evaluations being run, each with an associated transform",
    )
    summary_results: AgenticSummaryResults = Field(
        description="Summary of results across all test cases",
    )


# Pagination schemas
class AgenticExperimentListResponse(BasePaginationResponse):
    """Paginated list of agentic experiments"""

    data: list[AgenticExperimentSummary] = Field(
        description="List of agentic experiment summaries",
    )


# Test case / result schemas
class AgenticOutput(BaseModel):
    """Output from an agent HTTP request execution"""

    response_body: Dict[str, Any] = Field(
        description="Response body from the agent endpoint",
    )
    status_code: Optional[int] = Field(
        default=None,
        description="HTTP status code (None if request failed before receiving a response)",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Trace ID if available from the response",
    )


class AgenticResult(BaseResult):
    """Results from an agent execution with evals"""

    request_url: str = Field(description="URL that was called")
    request_headers: Dict[str, str] = Field(
        description="Headers that were sent (with variables resolved)",
    )
    request_body: str = Field(
        description="Request body that was sent (with variables resolved)",
    )
    output: Optional[AgenticOutput] = Field(
        default=None,
        description="Output from the agent (None if not yet executed)",
    )


class AgenticTestCase(BaseTestCase):
    """Individual test case result for agentic experiment"""

    template_input_variables: list[InputVariable] = Field(
        description="Input variables used in the template (with values resolved)",
    )
    agentic_result: AgenticResult = Field(
        description="Result from the agent execution",
    )


class AgenticTestCaseListResponse(BasePaginationResponse):
    """Paginated list of agentic test cases"""

    data: list[AgenticTestCase] = Field(description="List of test cases")


class AgenticConfigResult(BaseConfigResult):
    """Result for an agentic experiment test case"""

    template_input_variables: list[InputVariable] = Field(
        description="Input variables used in the template (with values resolved)",
    )
    request_url: str = Field(description="URL that was called")
    request_headers: Dict[str, str] = Field(
        description="Headers that were sent (with variables resolved)",
    )
    request_body: str = Field(
        description="Request body that was sent (with variables resolved)",
    )
    output: Optional[AgenticOutput] = Field(
        default=None,
        description="Output from the agent (None if not yet executed)",
    )


class AgenticConfigResultListResponse(BasePaginationResponse):
    """Paginated list of results for agentic experiments"""

    data: list[AgenticConfigResult] = Field(
        description="List of results for the agentic experiment",
    )
