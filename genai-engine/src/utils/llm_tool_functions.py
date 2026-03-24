import re
from typing import Any, Dict, List, Optional

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

ALLOWED_DELETE_PATTERNS = [
    re.compile(r"^/api/v1/tasks/[^/]+/llm_evals/[^/]+/versions/[^/]+/tags/[^/]+$"),
    re.compile(r"^/api/v1/tasks/[^/]+/prompts/[^/]+/versions/[^/]+/tags/[^/]+$"),
]


def resolve_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        node = node.get(part, {})
    return node


def is_allowed_delete_path(path: str) -> bool:
    return any(p.match(path) for p in ALLOWED_DELETE_PATTERNS)


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


def is_blacklisted(path: str, blacklist: List[str]) -> bool:
    for entry in blacklist:
        # Strip method prefix and description (e.g. "GET /api/v1/... - description" -> "/api/v1/...")
        parts = entry.split(" ", 1)
        pattern_path = parts[1] if len(parts) > 1 else parts[0]
        pattern_path = pattern_path.split(" - ")[0]
        # Replace path parameters like {task_id} with regex before escaping the rest
        segments = re.split(r"(\{[^}]+\})", pattern_path)
        regex = "".join(
            "[^/]+" if s.startswith("{") else re.escape(s) for s in segments
        )
        if re.match(f"^{regex}$", path):
            return True
    return False


def build_condensed_index(
    openapi_spec: Dict[str, Any],
    blacklist: Optional[List[str]] = None,
) -> List[str]:
    lines = []
    paths = openapi_spec.get("paths", {})
    for path, path_item in sorted(paths.items()):
        if blacklist and is_blacklisted(path, blacklist):
            continue
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
            lines.append(f"{method.upper()} {path} - {summary}{param_str}{body_str}")
    return lines


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
