import ssl
from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GenaiEngineOpenAIProvider(Enum):
    OPENAI = "OpenAI"
    AZURE = "Azure"


# Local path where docker-entrypoint.sh writes the private cert downloaded from
# GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL (mirrors postgres-cert.pem /
# keycloak-cert.pem).
OPENAI_PRIVATE_CERT_PATH = "openai-cert.pem"


class OpenAISettings(BaseSettings):
    GENAI_ENGINE_OPENAI_PROVIDER: GenaiEngineOpenAIProvider = (
        GenaiEngineOpenAIProvider.AZURE
    )
    GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD: int
    GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS: int
    GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS: str | None = Field(...)
    GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS: str | None = Field(
        default=None,
    )
    OPENAI_API_VERSION: str | None = Field(default="2025-02-01-preview")
    # TLS verification for outbound LLM / OpenAI-compatible proxy calls. Mirrors the
    # Postgres/Keycloak private-cert pattern: GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL
    # is fetched by docker-entrypoint.sh into OPENAI_PRIVATE_CERT_PATH and trusted as the
    # CA for the LLM endpoint (e.g. a LiteLLM proxy fronted with a private/self-signed
    # cert). Set GENAI_ENGINE_OPENAI_VERIFY_SSL=false to disable verification entirely
    # (insecure; dev/test only).
    GENAI_ENGINE_OPENAI_VERIFY_SSL: bool = True
    GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_ssl_verify(self) -> ssl.SSLContext | bool | None:
        """Resolve the TLS verification setting for outbound LLM/proxy calls.

        Returns a value suitable for httpx's ``verify`` argument, or ``None`` to keep
        httpx's default (certifi) behavior unchanged so existing deployments are
        unaffected.

        - When GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL is set, docker-entrypoint.sh
          has downloaded the cert to OPENAI_PRIVATE_CERT_PATH; trust it as the CA. Built
          as an ``ssl.SSLContext`` because httpx 0.28 deprecated ``verify=<str path>``.
        - Otherwise ``GENAI_ENGINE_OPENAI_VERIFY_SSL=false`` disables verification
          entirely (insecure; dev/test only).
        """
        if self.GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL:
            return ssl.create_default_context(cafile=OPENAI_PRIVATE_CERT_PATH)
        if not self.GENAI_ENGINE_OPENAI_VERIFY_SSL:
            return False
        return None

    @field_validator("GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS")
    @classmethod
    def check_url_for_genai_engine_openai_gpt_names_endpoints_keys(
        cls,
        value: str | None,
    ) -> str:
        return _check_url(value, "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS")

    @field_validator("GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS")
    @classmethod
    def check_url_for_genai_engine_openai_embeddings_names_endpoints_keys(
        cls,
        value: str | None,
    ) -> str:
        if value:
            return _check_url(
                value,
                "GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS",
            )
        return ""


def _check_url(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(
            f"The endpoint URLs in {field_name} must not be None",
        )
    items = value.split(",")
    for item in items:
        endpoint_data = item.split("::")
        url = endpoint_data[1] if len(endpoint_data) > 1 else ""
        # An empty endpoint is valid (OpenAI provider with no custom base_url, e.g.
        # "model_name::::api_key"); only enforce the trailing slash when one is given.
        if url and not url.endswith("/"):
            raise ValueError(
                f"The endpoint URLs in {field_name} must end with '/'",
            )
    return value
