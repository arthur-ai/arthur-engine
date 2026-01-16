import logging
from typing import Any, Callable

from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import MetricType, ToolClassEnum
from arthur_common.models.metric_schemas import (
    MetricRequest,
)
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.runnables import RunnableSerializable
from langchain_openai.chat_models import AzureChatOpenAI, ChatOpenAI
from pydantic import BaseModel, Field

from schemas.internal_schemas import MetricResult
from schemas.metric_schemas import MetricScoreDetails, ToolSelectionCorrectnessMetric
from scorer.llm_client import get_llm_executor
from scorer.metrics.tool_selection.prompt_templates import (
    TOOL_SELECTION_NON_STRUCTURED_PROMPT_TEMPLATE,
    TOOL_SELECTION_STRUCTURED_PROMPT_TEMPLATE,
    TOOL_USAGE_NON_STRUCTURED_PROMPT_TEMPLATE,
    TOOL_USAGE_STRUCTURED_PROMPT_TEMPLATE,
)
from scorer.scorer import MetricScorer

logger = logging.getLogger(__name__)


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


def get_model(temperature: float = 0.0) -> AzureChatOpenAI | ChatOpenAI:
    model = get_llm_executor().get_gpt_model(chat_temperature=temperature)
    if model is None:
        raise RuntimeError(
            "Failed to initialize LLM model for ToolSelectionCorrectnessScorer. "
            "Check your LLM configuration.",
        )
    return model


# Structured output chains
def get_tool_selection_chain_structured(
    temperature: float = 0.0,
) -> RunnableSerializable[dict[str, str | None], ToolSelectionResponseSchema]:
    """Structured output chain for tool selection"""
    model = get_model(temperature)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "context"],
        template=TOOL_SELECTION_STRUCTURED_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model.with_structured_output(ToolSelectionResponseSchema)
    return evaluation_chain  # type: ignore[return-value]


def get_tool_usage_chain_structured(
    temperature: float = 0.0,
) -> RunnableSerializable[dict[str, str | None], ToolUsageResponseSchema]:
    """Structured output chain for tool usage"""
    model = get_model(temperature)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "context"],
        template=TOOL_USAGE_STRUCTURED_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model.with_structured_output(ToolUsageResponseSchema)
    return evaluation_chain  # type: ignore[return-value]


# Legacy chains with JSON parser
def get_tool_selection_chain_legacy(
    temperature: float = 0.0,
) -> RunnableSerializable[dict[str, str | None], ToolSelectionResponseSchema]:
    """Legacy chain for tool selection with JSON parser"""
    model = get_model(temperature)
    parser = JsonOutputParser(pydantic_object=ToolSelectionResponseSchema)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "context"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
        },
        template=TOOL_SELECTION_NON_STRUCTURED_PROMPT_TEMPLATE,
    )
    evaluation_chain = pt | model | parser
    return evaluation_chain


def get_tool_usage_chain_legacy(
    temperature: float = 0.0,
) -> RunnableSerializable[dict[str, str | None], ToolUsageResponseSchema]:
    """Legacy chain for tool usage with JSON parser"""
    model = get_model(temperature)

    parser = JsonOutputParser(pydantic_object=ToolUsageResponseSchema)
    pt = PromptTemplate(
        input_variables=["system_prompt", "user_query", "context"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
        },
        template=TOOL_USAGE_NON_STRUCTURED_PROMPT_TEMPLATE,
    )

    evaluation_chain = pt | model | parser
    return evaluation_chain


# Legacy functions for backward compatibility
def get_tool_selection_chain(
    temperature: float = 0.0,
) -> RunnableSerializable[dict[str, str | None], ToolSelectionResponseSchema]:
    """Legacy function - uses structured outputs if supported, falls back to legacy"""
    if get_llm_executor().supports_structured_outputs():
        return get_tool_selection_chain_structured(temperature)
    else:
        return get_tool_selection_chain_legacy(temperature)


def get_tool_usage_chain(
    temperature: float = 0.0,
) -> RunnableSerializable[dict[str, str | None], ToolUsageResponseSchema]:
    """Legacy function - uses structured outputs if supported, falls back to legacy"""
    if get_llm_executor().supports_structured_outputs():
        return get_tool_usage_chain_structured(temperature)
    else:
        return get_tool_usage_chain_legacy(temperature)


class ToolSelectionCorrectnessScorer(MetricScorer):
    def __init__(self) -> None:
        super().__init__()

    def _get_chains(
        self,
    ) -> tuple[
        RunnableSerializable[dict[str, str | None], ToolSelectionResponseSchema],
        RunnableSerializable[dict[str, str | None], ToolUsageResponseSchema],
    ]:
        """Get the appropriate chains based on structured output support"""
        if get_llm_executor().supports_structured_outputs():
            return (
                get_tool_selection_chain_structured(),
                get_tool_usage_chain_structured(),
            )
        else:
            return get_tool_selection_chain_legacy(), get_tool_usage_chain_legacy()

    @staticmethod
    def prompt_llm(
        f: Callable[[], Any],
        operation_name: str,
    ) -> tuple[Any, LLMTokenConsumption]:
        """Execute chain with token tracking, similar to relevance scorer"""
        return get_llm_executor().execute(f, operation_name)

    def invoke_chain(
        self,
        user_query: str,
        system_prompt: str,
        context: list[dict[str, Any]],
    ) -> tuple[dict[str, str | int], dict[str, int]]:
        tool_selection_chain, tool_usage_chain = self._get_chains()

        # Create lambda for tool selection chain
        tool_selection_call = lambda: tool_selection_chain.invoke(
            input={  # In newer versions of langchain this is a general type for input, ignore type for now
                "system_prompt": system_prompt,
                "user_query": user_query,
                "context": context,  # type: ignore[dict-item]
            },
        )

        # Create lambda for tool usage chain
        tool_usage_call = lambda: tool_usage_chain.invoke(
            input={  # In newer versions of langchain this is a general type for input
                "system_prompt": system_prompt,
                "user_query": user_query,
                "context": context,  # type: ignore[dict-item]
            },
        )

        default_tool_selection: dict[str, str | int] = {
            "tool_selection": 2,
            "tool_selection_reason": "Could not evaluate tool selection",
        }
        default_tool_usage: dict[str, str | int] = {
            "tool_usage": 2,
            "tool_usage_reason": "Could not evaluate tool usage",
        }
        default_tokens = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)
        # Execute chains using prompt_llm pattern
        try:
            tool_selection_response: dict[str, str | int]
            tool_selection_response, selection_tokens = self.prompt_llm(
                tool_selection_call,
                "Tool Selection Check",
            )
            # Convert Pydantic model to dict if using structured outputs
            if isinstance(tool_selection_response, ToolSelectionResponseSchema):
                tool_selection_response = tool_selection_response.model_dump()
        except Exception as e:
            tool_selection_response, selection_tokens = (
                default_tool_selection,
                default_tokens,
            )

        try:
            tool_usage_response: dict[str, str | int]
            # If tool selection is not 2, then we can evaluate tool usage
            if tool_selection_response["tool_selection"] != 2:
                tool_usage_response, usage_tokens = self.prompt_llm(
                    tool_usage_call,
                    "Tool Usage Check",
                )
                # Convert Pydantic model to dict if using structured outputs
                if isinstance(tool_usage_response, ToolUsageResponseSchema):
                    tool_usage_response = tool_usage_response.model_dump()
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

    def score(self, request: MetricRequest, config: dict[str, Any]) -> MetricResult:
        """Scores tool selection and tool use by the assistant in relevance to the user's query"""
        # Config is not used in this scorer
        _ = config

        user_query = request.user_query or ""
        system_prompt = request.system_prompt or ""
        context = request.context

        tool_response, total_tokens = self.invoke_chain(
            user_query,
            system_prompt,
            context,
        )
        # Translate integer values to ToolClassEnum
        tool_selection_enum = ToolClassEnum(int(tool_response["tool_selection"]))
        tool_usage_enum = ToolClassEnum(int(tool_response["tool_usage"]))

        logger.info(f"Tool Selection Result: {tool_selection_enum}, {tool_usage_enum}")
        return MetricResult(
            id="",  # This will be set by the calling code
            metric_type=MetricType.TOOL_SELECTION,
            details=MetricScoreDetails(
                tool_selection=ToolSelectionCorrectnessMetric(
                    tool_selection=tool_selection_enum,
                    tool_selection_reason=str(tool_response["tool_selection_reason"]),
                    tool_usage=tool_usage_enum,
                    tool_usage_reason=str(tool_response["tool_usage_reason"]),
                ),
            ),
            prompt_tokens=total_tokens["prompt_tokens"],
            completion_tokens=total_tokens["completion_tokens"],
            latency_ms=0,  # This will be set by the calling code
        )
