from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.json import JsonOutputParser
from pydantic import BaseModel, Field

from schemas.common_schemas import LLMTokenConsumption
from schemas.enums import MetricType, ToolClassEnum
from schemas.internal_schemas import MetricResult
from schemas.metric_schemas import (
    MetricRequest,
    MetricScoreDetails,
    ToolSelectionCorrectnessMetric,
)
from scorer.llm_client import get_llm_executor
from scorer.metrics.tool_selection.prompt_templates import (
    TOOL_SELECTION_PROMPT_TEMPLATE,
    TOOL_USAGE_PROMPT_TEMPLATE,
)
from scorer.scorer import MetricScorer


# Schemas to force JSON output to the right format
class ToolSelectionResponseSchema(BaseModel):
    tool_selection: int = Field(
        description="Class 0: Wrong tool selected, 1: Correct tool selected, 2: No Tool Selected/Not Available",
    )
    tool_selection_reason: str = Field(
        description="Explanation of why the tool selection was correct or incorrect",
    )


class ToolUsageResponseSchema(BaseModel):
    tool_usage: int = Field(
        description="Class 0: Incorrect tool usage, 1: Correct tool usage, 2: No Tool Used/Not Available",
    )
    tool_usage_reason: str = Field(
        description="Explanation of why the tool usage was correct or incorrect",
    )


def get_model(temperature=0.0):
    return get_llm_executor().get_gpt_model(chat_temperature=temperature)


# Chain to evaluate tool selection
def get_tool_selection_chain(temperature=0.0):
    model = get_model(temperature)
    parser = JsonOutputParser(pydantic_object=ToolSelectionResponseSchema)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "context"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
        },
        template=TOOL_SELECTION_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model | parser
    return evaluation_chain


# Chain to evaluate tool usage
def get_tool_usage_chain(temperature=0.0):
    model = get_model(temperature)

    parser = JsonOutputParser(pydantic_object=ToolUsageResponseSchema)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "context"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
        },
        template=TOOL_USAGE_PROMPT_TEMPLATE,
    )

    evaluation_chain = pt | model | parser
    return evaluation_chain


class ToolSelectionCorrectnessScorer(MetricScorer):
    def __init__(self):
        super().__init__()
        self.tool_selection_chain = get_tool_selection_chain()
        self.tool_usage_chain = get_tool_usage_chain()

    @staticmethod
    def prompt_llm(f, operation_name: str):
        """Execute chain with token tracking, similar to relevance scorer"""
        return get_llm_executor().execute(f, operation_name)

    def invoke_chain(self, user_query, system_prompt, context):
        # Create lambda for tool selection chain
        tool_selection_call = lambda: self.tool_selection_chain.invoke(
            {
                "system_prompt": system_prompt,
                "user_query": user_query,
                "context": context,
            },
        )

        # Create lambda for tool usage chain
        tool_usage_call = lambda: self.tool_usage_chain.invoke(
            {
                "system_prompt": system_prompt,
                "user_query": user_query,
                "context": context,
            },
        )

        default_tool_selection = {
            "tool_selection": 2,
            "tool_selection_reason": "Could not evaluate tool selection",
        }
        default_tool_usage = {
            "tool_usage": 2,
            "tool_usage_reason": "Could not evaluate tool usage",
        }
        default_tokens = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)
        # Execute chains using prompt_llm pattern
        try:
            tool_selection_response, selection_tokens = self.prompt_llm(
                tool_selection_call,
                "Tool Selection Check",
            )
        except Exception as e:
            tool_selection_response, selection_tokens = (
                default_tool_selection,
                default_tokens,
            )

        try:
            # If tool selection is not 2, then we can evaluate tool usage
            if tool_selection_response["tool_selection"] != 2:
                tool_usage_response, usage_tokens = self.prompt_llm(
                    tool_usage_call,
                    "Tool Usage Check",
                )
            else:
                tool_usage_response, usage_tokens = default_tool_usage, default_tokens
        except Exception as e:
            tool_usage_response, usage_tokens = default_tool_usage, default_tokens

        # Combine responses and sum tokens
        tool_response = {**tool_selection_response, **tool_usage_response}
        total_tokens = {
            "prompt_tokens": selection_tokens.prompt_tokens
            + usage_tokens.prompt_tokens,
            "completion_tokens": selection_tokens.completion_tokens
            + usage_tokens.completion_tokens,
        }

        return tool_response, total_tokens

    def score(self, request: MetricRequest, config: dict) -> MetricResult:
        """Scores tool selection and tool use by the assistant in relevance to the user's query"""
        # Config is not used in this scorer
        _ = config

        user_query = request.user_query
        system_prompt = request.system_prompt
        context = request.context

        tool_response, total_tokens = self.invoke_chain(
            user_query,
            system_prompt,
            context,
        )
        # Translate integer values to ToolClassEnum
        tool_selection_enum = ToolClassEnum(tool_response["tool_selection"])
        tool_usage_enum = ToolClassEnum(tool_response["tool_usage"])

        return MetricResult(
            id="",  # This will be set by the calling code
            metric_type=MetricType.TOOL_SELECTION,
            details=MetricScoreDetails(
                tool_selection=ToolSelectionCorrectnessMetric(
                    tool_selection=tool_selection_enum,
                    tool_selection_reason=tool_response["tool_selection_reason"],
                    tool_usage=tool_usage_enum,
                    tool_usage_reason=tool_response["tool_usage_reason"],
                ),
            ),
            prompt_tokens=total_tokens["prompt_tokens"],
            completion_tokens=total_tokens["completion_tokens"],
            latency_ms=0,  # This will be set by the calling code
        )
