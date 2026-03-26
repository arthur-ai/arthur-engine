# /// script
# requires-python = ">=3.12"
# dependencies = ["fastmcp==3.1.1", "httpx==0.28.1", "python-dotenv==1.1.1"]
# ///

import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

GENAI_ENGINE_API_KEY = os.environ.get("GENAI_ENGINE_MCP_API_KEY")
GENAI_ENGINE_BASEURL = os.environ.get("GENAI_ENGINE_BASEURL")

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

mcp = FastMCP("arthur-engine")

API_INDEX = None

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


def build_condensed_index(
    openapi_spec: Dict[str, Any],
) -> List[str]:
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
            param_parts = []
            for p in operation.get("parameters", []):
                if p.get("in") not in ("query", "path"):
                    continue
                schema = p.get("schema", {})
                if "$ref" in schema:
                    schema = resolve_ref(openapi_spec, schema["$ref"])
                enum = schema.get("enum")
                if enum:
                    param_parts.append(
                        f"{p['name']}=[{'|'.join(str(v) for v in enum)}]",
                    )
                else:
                    param_parts.append(p["name"])
            param_str = f" (params: {', '.join(param_parts)})" if param_parts else ""
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


async def fetch_api_index() -> List[str]:
    global API_INDEX
    if API_INDEX is None:
        async with httpx.AsyncClient(base_url=GENAI_ENGINE_BASEURL, timeout=10.0) as client:
            response = await client.get("/openapi.json")
            response.raise_for_status()
            spec = response.json()
        API_INDEX = build_condensed_index(spec)
    return API_INDEX


@mcp.tool()
async def search_arthur_api(query: str) -> str:
    """Search for Arthur Engine API endpoints by keyword. Use this to find the right endpoint and its required parameters before calling it."""
    index = await fetch_api_index()
    return search_api_index(index, query)


@mcp.tool()
async def list_tasks(
    task_ids: Optional[str] = None,
    task_name: Optional[str] = None,
    is_agentic: Optional[bool] = None,
    include_archived: Optional[bool] = None,
    only_archived: Optional[bool] = None,
    sort: str = "desc",
    page: int = 0,
    page_size: int = 10,
) -> str:
    """List and search tasks (use cases) in Arthur Engine.

    Args:
        task_ids: JSON-encoded list of task IDs to filter by, e.g. '["id1", "id2"]'.
        task_name: Substring to search task names by.
        is_agentic: Filter by agentic status. If not provided, returns both.
        include_archived: If true, include archived tasks alongside active ones.
        only_archived: If true, return only archived tasks. Takes precedence over include_archived.
        sort: Sort order: "asc" or "desc" (default "desc").
        page: Page number (default 0).
        page_size: Number of tasks per page (default 10, max 100).
    """
    headers = {
        "Authorization": f"Bearer {GENAI_ENGINE_API_KEY}",
        "Content-Type": "application/json",
    }
    body: Dict[str, Any] = {}
    if task_ids:
        try:
            body["task_ids"] = json.loads(task_ids)
        except (json.JSONDecodeError, TypeError):
            return "Error: task_ids must be a JSON-encoded list of strings"
    if task_name is not None:
        body["task_name"] = task_name
    if is_agentic is not None:
        body["is_agentic"] = is_agentic
    if include_archived is not None:
        body["include_archived"] = include_archived
    if only_archived is not None:
        body["only_archived"] = only_archived

    params = {"sort": sort, "page": page, "page_size": page_size}

    try:
        async with httpx.AsyncClient(base_url=GENAI_ENGINE_BASEURL, timeout=30.0) as client:
            response = await client.post(
                "/api/v2/tasks/search",
                json=body,
                params=params,
                headers=headers,
            )
        return f"HTTP {response.status_code}\n{response.text}"
    except Exception as e:
        return f"Internal error: {str(e)}"


@mcp.tool()
async def call_arthur_api(
    method: str,
    path: str,
    query_params: Optional[str] = None,
    body: Optional[str] = None,
) -> str:
    """Call an Arthur Engine API endpoint. Routes with task ID need the UUID of the task, not the name.

    For DELETE requests, only these endpoints are permitted:
    - /api/v1/tasks/{task_id}/llm_evals/{eval_id}/versions/{version_id}/tags/{tag}
    - /api/v1/tasks/{task_id}/prompts/{prompt_id}/versions/{version_id}/tags/{tag}

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        path: API path, e.g. /api/v1/tasks/my-task/prompts
        query_params: JSON-encoded query parameters, e.g. {"page": 1, "size": 10}
        body: JSON-encoded request body for POST/PUT/PATCH requests
    """
    method = method.upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return f"Unsupported HTTP method: {method}"

    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        return "Invalid path: absolute URLs are not permitted"

    if method == "DELETE" and not is_allowed_delete_path(parsed.path):
        return "DELETE is only permitted for tag endpoints"

    try:
        parsed_query_params: Optional[Dict[str, Any]] = json.loads(query_params) if query_params else None
    except (json.JSONDecodeError, TypeError):
        parsed_query_params = None

    try:
        parsed_body: Optional[Dict[str, Any]] = json.loads(body) if body else None
    except (json.JSONDecodeError, TypeError):
        parsed_body = None

    headers = {
        "Authorization": f"Bearer {GENAI_ENGINE_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(base_url=GENAI_ENGINE_BASEURL, timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=path,
                params=parsed_query_params,
                json=parsed_body,
                headers=headers,
            )
        return f"HTTP {response.status_code}\n{response.text}"
    except Exception as e:
        return f"Internal error: {str(e)}"


if __name__ == "__main__":
    if GENAI_ENGINE_BASEURL is None:
        raise ValueError("GENAI_ENGINE_BASEURL is not set")
    if GENAI_ENGINE_API_KEY is None:
        raise ValueError("GENAI_ENGINE_MCP_API_KEY is not set")

    mcp.run(transport="stdio")
