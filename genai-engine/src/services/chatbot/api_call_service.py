import logging
import posixpath
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from utils.llm_tool_functions import is_allowed_delete_path, is_blacklisted

logger = logging.getLogger(__name__)


class ApiCallResult(BaseModel):
    method: str
    path: str
    status_code: int
    body: str

    def to_tool_result_content(self) -> str:
        return f"HTTP {self.status_code}\n{self.body}"


class ApiCallService:
    def __init__(
        self,
        token: str,
        base_url: str,
        blacklist: Optional[List[str]] = None,
    ):
        self.token = token
        self.base_url = base_url
        self.blacklist = blacklist or []

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

        normalized_path = posixpath.normpath(parsed.path)

        if method == "DELETE" and not is_allowed_delete_path(normalized_path):
            return ApiCallResult(
                method=method,
                path=path,
                status_code=403,
                body="DELETE is only permitted for tag endpoints",
            )

        if is_blacklisted(normalized_path, self.blacklist):
            return ApiCallResult(
                method=method,
                path=path,
                status_code=403,
                body="This endpoint has been blocked by the administrator",
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
                    url=normalized_path,
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
