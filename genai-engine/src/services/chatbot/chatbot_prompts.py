import functools
from typing import Any, Dict, List

from arthur_common.models.llm_model_providers import (
    JsonPropertySchema,
    JsonSchema,
    LLMTool,
    ToolFunction,
)
from fastapi import FastAPI

ALLOWED_TAGS = {
    "Transforms",
    "Continuous Evals",
    "Agentic Experiments",
    "Agentic Notebooks",
    "RAG Notebooks",
    "LLMEvals",
    "Datasets",
    "Prompts",
    "Users",
    "Sessions",
    "Spans",
    "Traces",
    "Notebooks",
    "RAG Experiments",
    "Prompt Experiments",
    "RAG Providers",
    "RAG Settings",
}

SYSTEM_PROMPT = """
You are an assistant for Arthur AI — an agentic development, monitoring, and observability platform for LLM applications.

Arthur AI helps users:
- Manage LLM prompts. Variables in prompts use mustache formatting (i.e. two open and two close curly braces around the variable name). Messages and tool_calls use OpenAI formatting.
- Create LLM-as-a-judge evaluators (llm_evals) and continuous evals that run automatically over incoming traces. All evals, must be scored on a binary scale with 0 being fail and 1 being pass.
- Generally, when a user refers to an "eval" it means an evaluator not evaluation.
- Run experiments: prompt experiments (A/B test prompts), RAG experiments (test retrieval pipelines), and agentic experiments (end-to-end agent evaluation). All experiments require a dataset.
- Monitor live traffic via spans and traces (stored in OpenInference format, e.g. attributes.input_messages for all input messages, attributes.input_messages.0.value for the first)
- Configure transforms — mappings from a named variable to a span path in OpenInference spec, used to extract values from traces for evaluation
- Manage RAG providers and RAG settings for retrieval-augmented generation pipelines
- Organize work into notebooks (agentic notebooks, RAG notebooks)

Instructions:
- Use search_arthur_api to find the right endpoint before calling it. When you decide to search, don't tell users you are searching for the endpoint. Just mention that you are starting to help them with their request.
- For GET requests, pass parameters as query_params
- For POST/PUT/PATCH, pass the request body as JSON
- You may only call DELETE endpoints for deleting tags. If a user asks to delete any other item, you must refuse their request immediately.
- Summarize results clearly in natural language; don't dump raw JSON unless the user asks
- When presenting lists of items with multiple fields, use a markdown table
- If a required parameter is missing, ask the user before calling the API
- When a user asks for the "most recent" or "latest" item, you should use the created_at datetime as the time the user is asking about. Do not assume the list returned from the list endpoint is sorted properly.
- When a user asks a follow-up question, no need to mention that you are responding based on chat history.
- Always end with a brief message to the user summarizing what was done or answering their question
"""

SEARCH_ARTHUR_API_TOOL = LLMTool(
    type="function",
    function=ToolFunction(
        name="search_arthur_api",
        description="Search for Arthur Engine API endpoints by keyword. Use this to find the right endpoint and its required parameters before calling it.",
        parameters=JsonSchema(
            type="object",
            properties={
                "query": JsonPropertySchema(
                    type="string",
                    description='Keywords to search for, e.g. "prompt versions" or "delete tag"',
                ),
            },
            required=["query"],
        ),
    ),
)

CALL_ARTHUR_API_TOOL = LLMTool(
    type="function",
    function=ToolFunction(
        name="call_arthur_api",
        description="Call an Arthur Engine API endpoint",
        parameters=JsonSchema(
            type="object",
            properties={
                "method": JsonPropertySchema(
                    type="string",
                    description="HTTP method (GET, POST, PUT, PATCH, DELETE)",
                    enum=["GET", "POST", "PUT", "PATCH", "DELETE"],
                ),
                "path": JsonPropertySchema(
                    type="string",
                    description="API path, e.g. /api/v1/tasks/my-task/prompts",
                ),
                "query_params": JsonPropertySchema(
                    type="string",
                    description='JSON-encoded query parameters, e.g. {"page": 1, "size": 10}',
                ),
                "body": JsonPropertySchema(
                    type="string",
                    description="JSON-encoded request body for POST/PUT/PATCH requests",
                ),
            },
            required=["method", "path"],
        ),
    ),
)


def resolve_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        node = node.get(part, {})
    return node


def get_required_body_fields(
    spec: Dict[str, Any],
    operation: Dict[str, Any],
) -> List[str]:
    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {})
    schema = content.get("application/json", {}).get("schema", {})
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])
    return list(schema.get("required", []))


def build_condensed_index(openapi_spec: Dict[str, Any]) -> List[str]:
    lines = []
    paths = openapi_spec.get("paths", {})
    for path, path_item in sorted(paths.items()):
        for method, operation in path_item.items():
            method = method.upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            # Exclude DELETE endpoints unless they are tag endpoints
            path_segments = path.rstrip("/").split("/")
            is_tag_endpoint = len(path_segments) >= 2 and path_segments[-2] == "tags"
            if method == "DELETE" and not is_tag_endpoint:
                continue
            tags = operation.get("tags", [])
            if not any(t in ALLOWED_TAGS for t in tags):
                continue
            summary = operation.get("summary", "")
            params = [
                p["name"]
                for p in operation.get("parameters", [])
                if p.get("in") in ("query", "path")
            ]
            param_str = f" (params: {', '.join(params)})" if params else ""
            body_str = ""
            if method in {"POST", "PUT", "PATCH"}:
                required_fields = get_required_body_fields(openapi_spec, operation)
                if required_fields:
                    body_str = f" (required body: {', '.join(required_fields)})"
            lines.append(f"{method.upper()} {path} - {summary}{param_str}{body_str}")
    return lines


@functools.lru_cache(maxsize=1)
def get_api_index(app: FastAPI) -> List[str]:
    spec = app.openapi()
    return build_condensed_index(spec)


def search_api_index(index: List[str], query: str) -> str:
    query_lower = query.lower()
    terms = query_lower.split()
    results = [line for line in index if all(t in line.lower() for t in terms)]
    if not results:
        # Fall back to any-term match
        results = [line for line in index if any(t in line.lower() for t in terms)]
    if not results:
        return "No matching endpoints found."
    return "\n".join(results[:20])
