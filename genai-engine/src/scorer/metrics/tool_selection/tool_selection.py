import logging
from typing import Any

from arthur_common.models.common_schemas import LLMTokenConsumption
from arthur_common.models.enums import MetricType, ToolClassEnum
from arthur_common.models.metric_schemas import (
    MetricRequest,
)
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from schemas.internal_schemas import MetricResult
from schemas.metric_schemas import MetricScoreDetails, ToolSelectionCorrectnessMetric
from scorer.judge_model import LLMJudge, resolve_judge
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


INPUT_VARIABLES = ["system_prompt", "user_query", "context"]


def run_tool_judge(
    judge: LLMJudge,
    structured_template: str,
    legacy_template: str,
    schema: type[ToolSelectionResponseSchema] | type[ToolUsageResponseSchema],
    inputs: dict[str, Any],
    operation: str,
) -> tuple[dict[str, str | int], LLMTokenConsumption]:
    """Ask the judge to classify tool selection or usage, with structured output when
    the model supports it and a JSON prompt otherwise."""
    if judge.supports_structured_output():
        pt = PromptTemplate(
            input_variables=INPUT_VARIABLES,
            template=structured_template,
        )
        response, tokens = judge.structured(pt, inputs, schema, operation)
        return response.model_dump(), tokens
    parser = JsonOutputParser(pydantic_object=schema)
    pt = PromptTemplate(
        input_variables=INPUT_VARIABLES,
        partial_variables={"format_instructions": parser.get_format_instructions()},
        template=legacy_template,
    )
    text, tokens = judge.text(pt, inputs, operation)
    return schema.model_validate(parser.parse(text)).model_dump(), tokens


class ToolSelectionCorrectnessScorer(MetricScorer):
    def __init__(self) -> None:
        super().__init__()

    def invoke_chain(
        self,
        user_query: str,
        system_prompt: str,
        context: list[dict[str, Any]],
    ) -> tuple[dict[str, str | int], dict[str, int]]:
        inputs: dict[str, Any] = {
            "system_prompt": system_prompt,
            "user_query": user_query,
            "context": context,
        }

        default_tool_selection: dict[str, str | int] = {
            "tool_selection": 2,
            "tool_selection_reason": "Could not evaluate tool selection",
        }
        default_tool_usage: dict[str, str | int] = {
            "tool_usage": 2,
            "tool_usage_reason": "Could not evaluate tool usage",
        }
        default_tokens = LLMTokenConsumption(prompt_tokens=0, completion_tokens=0)
        try:
            judge = resolve_judge(temperature=0.0)
        except Exception:
            judge = None
        if judge is None:
            return {**default_tool_selection, **default_tool_usage}, {
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
        try:
            tool_selection_response, selection_tokens = run_tool_judge(
                judge,
                TOOL_SELECTION_STRUCTURED_PROMPT_TEMPLATE,
                TOOL_SELECTION_NON_STRUCTURED_PROMPT_TEMPLATE,
                ToolSelectionResponseSchema,
                inputs,
                "Tool Selection Check",
            )
        except Exception as e:
            tool_selection_response, selection_tokens = (
                default_tool_selection,
                default_tokens,
            )

        try:
            tool_usage_response: dict[str, str | int]
            # If tool selection is not 2, then we can evaluate tool usage
            if tool_selection_response["tool_selection"] != 2:
                tool_usage_response, usage_tokens = run_tool_judge(
                    judge,
                    TOOL_USAGE_STRUCTURED_PROMPT_TEMPLATE,
                    TOOL_USAGE_NON_STRUCTURED_PROMPT_TEMPLATE,
                    ToolUsageResponseSchema,
                    inputs,
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
