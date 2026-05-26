import json

from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Function,
    TokenCountResponse,
)

from schemas.response_schemas import AgenticPromptRunResponse


async def make_stream(events: list[str]):
    for event in events:
        yield event


def parse_sse_event(body: str, event_name: str) -> dict:
    """Return the JSON-parsed data payload of the first SSE event named `event_name`."""
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == f"event: {event_name}" and i + 1 < len(lines):
            data_line = lines[i + 1]
            if data_line.startswith("data: "):
                return json.loads(data_line[len("data: ") :])
    raise AssertionError(f"event '{event_name}' not found in stream")


def make_tool_call(id: str, name: str, arguments: str) -> ChatCompletionMessageToolCall:
    return ChatCompletionMessageToolCall(
        id=id,
        type="function",
        function=Function(name=name, arguments=arguments),
    )


def final_response_events(content: str) -> list[str]:
    payload = AgenticPromptRunResponse(
        content=content,
        tool_calls=None,
        cost="0.0",
    ).model_dump_json()
    return [f"event: final_response\ndata: {payload}\n\n"]


def make_token_count_response(total: int) -> TokenCountResponse:
    return TokenCountResponse(
        total_tokens=total,
        request_model="test-model",
        model_used="test-model",
        tokenizer_type="test",
    )
