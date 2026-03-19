import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ApiCallResult:
    def __init__(self, method: str, path: str, status_code: int, body: str):
        self.method = method
        self.path = path
        self.status_code = status_code
        self.body = body

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
                method,
                path,
                400,
                f"Unsupported HTTP method: {method}",
            )
        if method == "DELETE" and "/tags/" not in path:
            return ApiCallResult(
                method,
                path,
                403,
                "DELETE is only permitted for tag endpoints",
            )

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=path,
                    params=query_params,
                    json=body,
                    headers=headers,
                )
            return ApiCallResult(method, path, response.status_code, response.text)
        except Exception as e:
            logger.error(f"ApiCallService error calling {method} {path}: {e}")
            return ApiCallResult(method, path, 500, f"Internal error: {str(e)}")
