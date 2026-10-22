import os
import random
from dataclasses import replace
from uuid import UUID

import httpx
import litellm
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from openai import AzureOpenAI, OpenAI
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.openai_config import (
    GenaiEngineOpenAIProvider,
    GuardrailEnvironmentSettings,
    GuardrailRateSettings,
    OpenAITransportSettings,
)
from db_models import DatabaseOrganization
from dependencies import db_session_context
from repositories.guardrail_configuration_repository import (
    GuardrailConfigurationRepository,
    lock_guardrail_configuration,
)
from repositories.model_provider_repository import ModelProviderRepository
from repositories.organizations_repository import (
    enforce_token_quota,
    record_org_token_usage,
)
from schemas.guardrail_schemas import GuardrailLLMConfiguration
from services.guardrails.judge_executor import (
    CONFIGURATION_UNAVAILABLE,
    NOT_CONFIGURED,
    EnvironmentJudgeHandle,
    JudgeContext,
    ProviderJudgeHandle,
    get_judge_rate_limiter,
)
from utils import constants
from utils.utils import get_env_var


def validate_guardrail_selection(
    session: Session, selection: GuardrailLLMConfiguration
) -> None:
    repository = ModelProviderRepository(session)
    try:
        catalog = repository.list_catalog_models_for_provider(selection.provider)
    except Exception:
        raise HTTPException(
            status_code=400, detail="Unable to load the provider model catalog."
        ) from None
    lock_guardrail_configuration(session)
    try:
        client = repository.get_model_provider_client(selection.provider)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Configure the model provider before selecting a guardrail model.",
        ) from None
    aliases_allowed = selection.provider == ModelProvider.AZURE or (
        selection.provider == ModelProvider.OPENAI and bool(client.api_base)
    )
    if not aliases_allowed and selection.model not in catalog:
        raise HTTPException(
            status_code=400, detail="Select a model from the provider catalog."
        )
    if selection.base_model is not None and (
        not aliases_allowed or selection.base_model not in catalog
    ):
        raise HTTPException(
            status_code=400,
            detail="Select a catalog base model for an Azure deployment or custom OpenAI endpoint.",
        )


def model_capabilities(
    provider: ModelProvider, model: str
) -> tuple[bool, int | None, bool]:
    prefix = f"{provider.value}/"
    unqualified = model.removeprefix(prefix)
    metadata = (
        litellm.model_cost.get(prefix + unqualified)
        or litellm.model_cost.get(unqualified)
        or {}
    )
    limit = next(
        (
            int(metadata[key])
            for key in ("max_input_tokens", "max_tokens")
            if isinstance(metadata.get(key), (int, float)) and metadata[key] > 0
        ),
        None,
    )
    try:
        structured = bool(
            litellm.supports_response_schema(
                model=model, custom_llm_provider=provider.value
            )
        )
    except Exception:
        structured = False
    try:
        parameters = (
            litellm.get_supported_openai_params(
                model=model, custom_llm_provider=provider.value
            )
            or []
        )
        temperature = "temperature" in parameters
    except Exception:
        temperature = False
    return structured, limit, temperature


def capture_judge_context(org_id: UUID) -> JudgeContext:
    settings_file = os.environ.get("OPENAI_CONFIG_FILE", ".env")
    try:
        with db_session_context() as session:
            if (
                session.execute(
                    select(DatabaseOrganization.id).where(
                        DatabaseOrganization.id == org_id
                    )
                ).scalar_one_or_none()
                is None
            ):
                return JudgeContext(org_id=org_id, error=CONFIGURATION_UNAVAILABLE)
            lock_guardrail_configuration(session, shared=True)
            selection, status = GuardrailConfigurationRepository(session).read()
            if status == "invalid":
                return JudgeContext(org_id=org_id, error=CONFIGURATION_UNAVAILABLE)
            client = (
                ModelProviderRepository(session).get_model_provider_client(
                    selection.provider
                )
                if selection is not None and status == "configured"
                else None
            )
        rates = GuardrailRateSettings(_env_file=settings_file)
        limiter = get_judge_rate_limiter(
            rates.GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD,
            rates.GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS,
        )
        if selection is not None and client is not None:
            metadata_model = selection.base_model or selection.model
            structured, limit, temperature = model_capabilities(
                selection.provider, metadata_model
            )
            transport = OpenAITransportSettings(_env_file=settings_file)
            sdk_client: OpenAI | AzureOpenAI | None = None
            if selection.provider in (ModelProvider.OPENAI, ModelProvider.AZURE):
                if not client.api_key or (
                    selection.provider == ModelProvider.AZURE
                    and (not client.api_base or not client.api_version)
                ):
                    return JudgeContext(org_id=org_id, error=CONFIGURATION_UNAVAILABLE)
                verify = transport.get_ssl_verify()
                http_client = httpx.Client(verify=True if verify is None else verify)
                try:
                    if selection.provider == ModelProvider.AZURE:
                        sdk_client = AzureOpenAI(
                            api_key=client.api_key,
                            azure_endpoint=client.api_base,
                            api_version=client.api_version,
                            http_client=http_client,
                            max_retries=0,
                        )
                    else:
                        sdk_client = OpenAI(
                            api_key=client.api_key,
                            base_url=client.api_base or "https://api.openai.com/v1",
                            http_client=http_client,
                            max_retries=0,
                        )
                except Exception:
                    http_client.close()
                    raise
            return JudgeContext(
                org_id=org_id,
                provider=selection.provider,
                model=selection.model,
                metadata_model=metadata_model,
                structured_output=structured,
                input_limit=limit
                or int(
                    get_env_var(
                        constants.GENAI_ENGINE_HALLUCINATION_CHECK_MAX_TOKEN_LIMIT_ENV_VAR
                    )
                    or 8192
                ),
                handle=ProviderJudgeHandle(
                    client, sdk_client, org_id, selection.model, temperature
                ),
                limiter=limiter,
            )
        return replace(_environment_context(org_id, settings_file), limiter=limiter)
    except Exception:
        return JudgeContext(org_id=org_id, error=CONFIGURATION_UNAVAILABLE)


def _environment_context(org_id: UUID, settings_file: str) -> JudgeContext:
    settings = GuardrailEnvironmentSettings(_env_file=settings_file)
    contract = settings.GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
    if not contract:
        return JudgeContext(org_id=org_id, error=NOT_CONFIGURED)
    try:
        connections = [item.strip().split("::") for item in contract.split(",")]
        if any(
            len(item) != 3
            or not item[0]
            or not item[2]
            or (item[1] and not item[1].endswith("/"))
            for item in connections
        ):
            raise ValueError("Invalid environment connection.")
        model, endpoint, key = random.choice(connections)
        provider = (
            ModelProvider.AZURE
            if settings.GENAI_ENGINE_OPENAI_PROVIDER == GenaiEngineOpenAIProvider.AZURE
            else ModelProvider.OPENAI
        )
        structured, limit, temperature = model_capabilities(provider, model)
        verify = settings.get_ssl_verify()
        http_client = httpx.Client(verify=True if verify is None else verify)
        try:
            legacy_model: AzureChatOpenAI | ChatOpenAI
            if provider == ModelProvider.AZURE:
                legacy_model = AzureChatOpenAI(
                    azure_deployment=model,
                    azure_endpoint=endpoint or None,
                    api_key=SecretStr(key),
                    api_version=settings.OPENAI_API_VERSION,
                    temperature=0.0 if temperature else None,
                    http_client=http_client,
                    max_retries=0,
                )
            else:
                legacy_model = ChatOpenAI(
                    model=model,
                    base_url=endpoint or "https://api.openai.com/v1",
                    api_key=SecretStr(key),
                    temperature=0.0 if temperature else None,
                    http_client=http_client,
                    max_retries=0,
                )
        except Exception:
            http_client.close()
            raise
        return JudgeContext(
            org_id=org_id,
            provider=provider,
            model=model,
            metadata_model=model,
            structured_output=structured,
            input_limit=limit
            or int(
                get_env_var(
                    constants.GENAI_ENGINE_HALLUCINATION_CHECK_MAX_TOKEN_LIMIT_ENV_VAR
                )
                or 8192
            ),
            handle=EnvironmentJudgeHandle(
                legacy_model, org_id, enforce_token_quota, record_org_token_usage
            ),
        )
    except Exception:
        return JudgeContext(org_id=org_id, error=CONFIGURATION_UNAVAILABLE)
