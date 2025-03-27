from fastapi.security import HTTPBearer

http_bearer_scheme = HTTPBearer(
    scheme_name="API Key",
    description="Bearer token authentication with an API key",
    auto_error=False,
)
