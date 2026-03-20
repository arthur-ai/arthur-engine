import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ApiCallResult(BaseModel):
    method: str
    path: str
    status_code: int
    body: str

    def to_tool_result_content(self) -> str:
        return f"HTTP {self.status_code}\n{self.body}"


class ApiCallService:
    def __init__(self, token: str, base_url: str):
        self.token = token
        self.base_url = base_url

    async def call(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> ApiCallResult:
        method = method.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            return ApiCallResult(
                method=method,
                path=path,
                status_code=400,
                body=f"Unsupported HTTP method: {method}",
            )
        parsed = urlparse(path)
        if parsed.scheme or parsed.netloc:
            return ApiCallResult(
                method=method,
                path=path,
                status_code=400,
                body="Invalid path: absolute URLs are not permitted",
            )

        path_segments = parsed.path.rstrip("/").split("/")
        is_tag_endpoint = len(path_segments) >= 2 and path_segments[-2] == "tags"
        if method == "DELETE" and not is_tag_endpoint:
            return ApiCallResult(
                method=method,
                path=path,
                status_code=403,
                body="DELETE is only permitted for tag endpoints",
            )

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
            ) as client:
                response = await client.request(
                    method=method,
                    url=path,
                    params=query_params,
                    json=body,
                    headers=headers,
                )
            return ApiCallResult(
                method=method,
                path=path,
                status_code=response.status_code,
                body=response.text,
            )
        except Exception as e:
            logger.error(f"ApiCallService error calling {method} {path}: {e}")
            return ApiCallResult(
                method=method,
                path=path,
                status_code=500,
                body=f"Internal error: {str(e)}",
            )
