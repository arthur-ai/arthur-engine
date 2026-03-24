from typing import Any, Dict, List

from services.chatbot.chatbot_prompts import is_allowed_delete_path

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
            if method == "DELETE" and not is_allowed_delete_path(path):
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
            lines.append(f"{method} {path} - {summary}{param_str}{body_str}")
    return lines


def search_api_index(index: List[str], query: str) -> str:
    query_lower = query.lower()
    terms = query_lower.split()
    results = [line for line in index if all(t in line.lower() for t in terms)]
    if not results:
        results = [line for line in index if any(t in line.lower() for t in terms)]
    if not results:
        return "No matching endpoints found."
    return "\n".join(results[:20])
