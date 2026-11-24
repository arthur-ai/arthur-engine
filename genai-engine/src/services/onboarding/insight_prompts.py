"""The onboarding insight prompts, seeded into the Arthur system task at startup.

Before an agent is set up for monitoring, the ML engine's onboarding analysis asks each
of these of a sample of the agent's traces. It runs the prompt saved as
`onboarding_insight_<kind>` through the saved-prompt completions route, passing one
variable, `traces`: a batch of serialized traces after a FACTS block of per-trace hints.
The model answers with a JSON verdict.

The prompts name no model: they are saved with the 'empty' placeholder and run on the
instance's default model provider. Arthur owns the text below; a customer can still edit
a prompt (a new version), and the seeder never moves `production` off a version it did
not write.
"""

from arthur_common.models.llm_model_providers import (
    JsonPropertySchema,
    JsonSchema,
    LLMResponseFormat,
    LLMResponseFormatEnum,
    LLMResponseSchema,
)

ONBOARDING_INSIGHT_PROMPT_PREFIX = "onboarding_insight_"

# Room for the verdict, which is a few hundred tokens.
ONBOARDING_INSIGHT_MAX_TOKENS = 4_000

ONBOARDING_INSIGHT_SYSTEM_PROMPT = """You review a sample of traces from one AI agent, before it is set up for monitoring, and decide whether one property of the agent holds.

Each trace is a tree of spans in execution order: [n] numbers each span, children are indented under their parent. AGENT/CHAIN spans group work; LLM spans are model calls (in.* = what the model was given, out.* = what it produced, out.call X = a tool call it requested); TOOL spans are tool executions (args, result). A step failed if its span is marked ERROR or its result reports an error. If a trace is marked TRUNCATED, judge only what is shown. GUARDRAIL spans are validation checks, not the agent's own work.

Each trace has an id like t07. Before the traces you get FACTS: per-trace hints that cheap rules extracted. Facts are evidence, not the answer: check them against the traces.

"fired" is "yes" only when the traces show it; list every trace that shows it in matched_traces (empty when "no")."""

# One question per insight kind; the ML engine asks each of every batch.
ONBOARDING_INSIGHT_QUESTIONS = {
    "internet_access": "Does the agent connect to resources on the internet: do any TOOL calls fetch or send to a URL or an outside host? Internal lookups by id are not internet access.",
    "tool_output_to_llm": "Does the agent feed tool output straight into a later LLM call in the same trace, so text a tool returned becomes part of a model's input?",
    "reference_material": "Does the agent pull in reference material (documents, search results, knowledge-base passages, retrieval) to answer?",
    "user_facing": "Does the agent look user-facing: does it converse with end users (conversational turns, sessions, user ids, replies addressed to a person)?",
    "heavy_model": "Is the agent using a heavy, expensive model for a light task? Judge from the model names and what each call does. If model names are unknown or not real models, answer cannot_tell.",
    "tool_failures": "Do the agent's tool calls fail repeatedly? Name each tool with failures, how many of its calls failed, and whether the agent recovered (a later retry or alternative succeeded and the answer used it) or not.",
}


def onboarding_insight_user_message(kind: str) -> str:
    """The user message for one insight: the traces variable, then the question."""
    return (
        "{{ traces }}\n\n"
        f"Insight kind: {kind}\n"
        f"Question: {ONBOARDING_INSIGHT_QUESTIONS[kind]}"
    )


def onboarding_insight_response_format() -> LLMResponseFormat:
    """The verdict's JSON schema, which the model's reply must follow.

    Every kind gets the same schema: providers cache it as part of the prompt prefix,
    so a schema that differed per kind would stop the prompts of a batch from reading
    each other's cached traces."""
    return LLMResponseFormat(
        type=LLMResponseFormatEnum.JSON_SCHEMA,
        json_schema=LLMResponseSchema.model_validate(
            {
                "name": "onboarding_insight_verdict",
                "strict": True,
                "schema": JsonSchema(
                    properties={
                        "kind": JsonPropertySchema(
                            type="string",
                            description="The insight kind you were asked about.",
                            enum=list(ONBOARDING_INSIGHT_QUESTIONS),
                        ),
                        "fired": JsonPropertySchema(
                            type="string",
                            description="Whether the traces show it.",
                            enum=["yes", "no", "cannot_tell"],
                        ),
                        "matched_traces": JsonPropertySchema(
                            type="array",
                            description="Every trace id that shows it, e.g. t01; empty when fired is no.",
                            items={"type": "string"},
                        ),
                        "example_span_name": JsonPropertySchema(
                            type="string",
                            description="A span name that shows it, or an empty string.",
                        ),
                        "reason": JsonPropertySchema(
                            type="string",
                            description="2-4 sentences citing trace ids and span names.",
                        ),
                    },
                    required=[
                        "kind",
                        "fired",
                        "matched_traces",
                        "example_span_name",
                        "reason",
                    ],
                    additionalProperties=False,
                ),
            },
        ),
    )
