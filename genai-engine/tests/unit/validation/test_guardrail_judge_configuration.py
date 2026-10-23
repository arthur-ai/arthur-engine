import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from arthur_common.models.common_schemas import (
    KeywordsConfig,
    LLMTokenConsumption,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from arthur_common.models.enums import RuleResultEnum, RuleScope, RuleType
from arthur_common.models.llm_model_providers import ModelProvider
from arthur_common.models.request_schemas import NewRuleRequest
from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import dependencies
import server
from config.database_config import DatabaseConfig
from config.openai_config import GuardrailRateSettings
from db_models import DatabaseApplicationConfiguration, DatabaseOrganization
from db_models.secret_storage_models import DatabaseSecretStorage
from repositories.configuration_repository import ConfigurationRepository
from repositories.guardrail_configuration_repository import (
    GuardrailConfigurationRepository,
)
from repositories.model_provider_repository import ModelProviderRepository
from schemas.enums import ApplicationConfigurations
from schemas.guardrail_schemas import GuardrailLLMConfiguration
from schemas.internal_schemas import Rule, ValidationRequest
from schemas.request_schemas import ApplicationConfigurationUpdateRequest
from schemas.scorer_schemas import Example, RuleScore, ScoreRequest
from scorer.checks.sensitive_data.custom_examples import SensitiveDataCustomExamples
from services.guardrails import llm_configuration_service as configuration_service
from services.guardrails.judge_executor import (
    CONFIGURATION_UNAVAILABLE,
    NOT_CONFIGURED,
    JudgeCallResult,
    JudgeContext,
    JudgeEvaluation,
    JudgeRateLimiter,
    zero_tokens,
)
from services.guardrails.validation import evaluate_guardrails
from tests.clients.base_test_client import override_get_db_session
from utils import constants

pytestmark = pytest.mark.unit_tests


@pytest.mark.asyncio
async def test_startup_and_local_validation_without_judge_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_CONFIG_FILE", str(tmp_path / "absent.env"))
    for name in tuple(os.environ):
        if name.startswith("GENAI_ENGINE_OPENAI_"):
            monkeypatch.delenv(name)
    forbidden = MagicMock(
        side_effect=AssertionError("Local validation must not initialize a judge")
    )
    monkeypatch.setattr("scorer.llm_client.OpenAISettings", forbidden)
    monkeypatch.setattr(
        "services.guardrails.validation.capture_judge_context", forbidden
    )
    monkeypatch.setattr(dependencies, "SINGLETON_SCORER_CLIENT", None)
    local_classifier = MagicMock()
    local_classifier.score.return_value = RuleScore(
        result=RuleResultEnum.MODEL_NOT_AVAILABLE
    )
    monkeypatch.setattr(
        dependencies, "BinaryPIIDataClassifier", lambda: local_classifier
    )
    monkeypatch.setattr(
        dependencies, "BinaryPIIDataClassifierV1", lambda: local_classifier
    )
    for name in (
        "PROMPT_INJECTION_MODEL",
        "PROMPT_INJECTION_TOKENIZER",
        "TOXICITY_MODEL",
        "TOXICITY_TOKENIZER",
    ):
        monkeypatch.setattr(dependencies, name, None)
    monkeypatch.setattr(
        dependencies.BinaryPromptInjectionClassifier,
        "_download_model_and_tokenizer",
        lambda self: None,
    )
    monkeypatch.setattr(
        dependencies.ToxicityScorer, "_download_model_and_tokenizer", lambda self: None
    )
    monkeypatch.setattr(
        server, "get_db_session", lambda: iter([override_get_db_session()])
    )
    monkeypatch.setattr(
        server, "get_keycloak_settings", lambda: SimpleNamespace(ENABLED=False)
    )
    monkeypatch.setattr(server, "is_api_only_mode_enabled", lambda: True)
    monkeypatch.setattr(server, "relevance_models_enabled", lambda: False)
    monkeypatch.setattr(server, "initialize_system_tasks", lambda session: None)

    @contextmanager
    def session_context():
        with override_get_db_session() as session:
            yield session

    monkeypatch.setattr(server, "db_session_context", session_context)
    for name in (
        "send_telemetry_event",
        "initialize_continuous_eval_queue_service",
        "initialize_currency_conversion_service",
        "initialize_trace_retention_service",
        "shutdown_continuous_eval_queue_service",
        "shutdown_currency_conversion_service",
        "shutdown_trace_retention_service",
    ):
        monkeypatch.setattr(server, name, MagicMock())
    for name in (
        "download_models",
        "get_claim_classifier_embedding_model",
        "get_prompt_injection_model",
        "get_prompt_injection_tokenizer",
        "get_toxicity_model",
        "get_toxicity_tokenizer",
    ):
        monkeypatch.setattr(server.model_load, name, lambda *args: None)
    monkeypatch.setattr(
        "scorer.checks.hallucination.v2.get_claim_classifier", lambda *args: None
    )
    async with server.lifespan(server.get_test_app()):
        scorer = dependencies.get_scorer_client()
        configurations = [
            (RuleType.REGEX, RegexConfig(regex_patterns=["private"])),
            (RuleType.KEYWORD, KeywordsConfig(keywords=["private"])),
            (RuleType.PROMPT_INJECTION, None),
            (RuleType.PII_DATA, PIIConfig()),
            (RuleType.TOXICITY, ToxicityConfig(threshold=0.5)),
        ]
        rules = [
            Rule._from_request_model(
                NewRuleRequest(
                    name=kind.value,
                    type=kind,
                    apply_to_prompt=True,
                    apply_to_response=False,
                    config=config,
                ),
                RuleScope.TASK,
            )
            for kind, config in configurations
        ]
        results = evaluate_guardrails(
            ValidationRequest(prompt="public information"), rules, scorer, uuid4()
        )
        assert len(results) == len(rules)
    forbidden.assert_not_called()


@pytest.fixture
def judge_store(monkeypatch, tmp_path):
    engine = create_engine(**DatabaseConfig(TEST_DATABASE=True).get_connection_params())
    for model in (
        DatabaseOrganization,
        DatabaseApplicationConfiguration,
        DatabaseSecretStorage,
    ):
        model.__table__.create(engine)
    sessions = sessionmaker(engine)
    org_id = uuid4()
    with sessions() as session:
        session.add(
            DatabaseOrganization(
                id=org_id, name="judge-test", created_at=datetime.now()
            )
        )
        session.commit()

    @contextmanager
    def session_context():
        with sessions() as session:
            yield session

    monkeypatch.setattr(configuration_service, "db_session_context", session_context)
    monkeypatch.setenv("OPENAI_CONFIG_FILE", str(tmp_path / "absent.env"))
    for name in (
        "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
        "GENAI_ENGINE_OPENAI_PROVIDER",
        "GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD",
        "GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS",
        "GENAI_ENGINE_OPENAI_VERIFY_SSL",
        "GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    yield sessions, org_id
    engine.dispose()


def configure_provider(
    sessions,
    *,
    provider=ModelProvider.OPENAI,
    model="gpt-4o",
    endpoint=None,
    base_model=None,
):
    selection = GuardrailLLMConfiguration(
        provider=provider, model=model, base_model=base_model
    )
    with sessions() as session:
        ModelProviderRepository(session).set_model_provider_credentials(
            provider,
            api_key=SecretStr("local-test-credential"),
            api_base=SecretStr(endpoint) if endpoint else None,
            api_version=(
                "2025-02-01-preview" if provider == ModelProvider.AZURE else None
            ),
        )
        GuardrailConfigurationRepository(session).write(selection)
        session.commit()
    return selection


def test_config_precedence_and_automatic_fallback(judge_store, monkeypatch):
    sessions, org_id = judge_store
    assert configuration_service.capture_judge_context(org_id).error == NOT_CONFIGURED
    monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
    monkeypatch.setenv(
        "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
        "gpt-4o::http://127.0.0.1:9/::local-env-credential",
    )
    context = configuration_service.capture_judge_context(org_id)
    assert context.error is None
    assert context.model == "gpt-4o"
    context.close()
    configure_provider(sessions, model="gpt-4.1")
    context = configuration_service.capture_judge_context(org_id)
    assert context.model == "gpt-4.1"
    assert context.handle.client.api_key == "local-test-credential"
    context.close()
    with sessions() as session:
        ModelProviderRepository(session).delete_model_provider_credentials(
            ModelProvider.OPENAI
        )
        assert (
            GuardrailConfigurationRepository(session).read()[1] == "needs_configuration"
        )
    context = configuration_service.capture_judge_context(org_id)
    assert context.model == "gpt-4o"
    context.close()
    monkeypatch.delenv("GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS")
    assert configuration_service.capture_judge_context(org_id).error == NOT_CONFIGURED


def test_malformed_selection_never_activates_environment(judge_store, monkeypatch):
    sessions, org_id = judge_store
    monkeypatch.setenv(
        "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
        "gpt-4o::http://127.0.0.1:9/::local-env-credential",
    )
    with sessions() as session:
        session.add(
            DatabaseApplicationConfiguration(
                name=ApplicationConfigurations.GUARDRAIL_LLM,
                value='{"provider":"openai","model":"","mode":"legacy"}',
            )
        )
        session.commit()
        assert GuardrailConfigurationRepository(session).read() == (None, "invalid")
    fallback = MagicMock()
    monkeypatch.setattr(configuration_service, "_environment_context", fallback)
    assert (
        configuration_service.capture_judge_context(org_id).error
        == CONFIGURATION_UNAVAILABLE
    )
    fallback.assert_not_called()


def test_configuration_and_errors_do_not_expose_secrets(
    judge_store, monkeypatch, caplog
):
    sessions, org_id = judge_store
    configure_provider(sessions)
    private_endpoint = "https://private.example.test/credential"

    def fail(*args):
        raise ValueError(private_endpoint)

    monkeypatch.setattr(ModelProviderRepository, "get_model_provider_client", fail)
    fallback = MagicMock()
    monkeypatch.setattr(configuration_service, "_environment_context", fallback)
    context = configuration_service.capture_judge_context(org_id)
    assert context.error == CONFIGURATION_UNAVAILABLE
    assert private_endpoint not in repr(context) + caplog.text
    fallback.assert_not_called()
    assert (
        configuration_service.capture_judge_context(uuid4()).error
        == CONFIGURATION_UNAVAILABLE
    )


def test_request_snapshot_refreshes_across_sessions(judge_store):
    sessions, org_id = judge_store
    configure_provider(sessions, model="gpt-4o")
    before = configuration_service.capture_judge_context(org_id)
    configure_provider(sessions, model="gpt-4.1")
    after = configuration_service.capture_judge_context(org_id)
    try:
        assert before.model == "gpt-4o"
        assert after.model == "gpt-4.1"
        assert before.handle is not after.handle
        with sessions() as session:
            repository = GuardrailConfigurationRepository(session)
            with pytest.raises(HTTPException) as rejected:
                repository.authorize_provider_mutation(
                    ModelProvider.OPENAI, {constants.TASK_ADMIN}
                )
            assert rejected.value.status_code == 403
            repository.authorize_provider_mutation(
                ModelProvider.ANTHROPIC, {constants.TASK_ADMIN}
            )
            repository.authorize_provider_mutation(
                ModelProvider.OPENAI, {constants.ORG_ADMIN}
            )
    finally:
        before.close()
        after.close()


def test_guardrail_config_atomic_save_and_omission(judge_store):
    sessions, _ = judge_store
    selection = configure_provider(
        sessions,
        model="proxy/team/model",
        endpoint="http://127.0.0.1:9/proxy/v1/",
        base_model="gpt-4o",
    )
    with sessions() as session:
        repository = ConfigurationRepository(session)
        saved_secret = session.query(DatabaseSecretStorage).one().value
        result = repository.update_configurations(
            ApplicationConfigurationUpdateRequest(default_currency="EUR")
        )
        assert result.guardrail_llm == selection
        assert result.guardrail_llm_status == "configured"
        assert session.query(DatabaseSecretStorage).one().value == saved_secret
        result = repository.update_configurations(
            ApplicationConfigurationUpdateRequest(guardrail_llm=None)
        )
        assert result.guardrail_llm is None
        assert result.guardrail_llm_status == "needs_configuration"
        assert result.default_currency == "EUR"
    with pytest.raises(ValidationError):
        GuardrailLLMConfiguration(
            provider=ModelProvider.OPENAI, model="gpt-4o", mode="legacy"
        )


@pytest.mark.parametrize(
    ("provider", "endpoint", "model", "base_model", "accepted"),
    [
        (ModelProvider.OPENAI, None, "not-in-catalog", None, False),
        (ModelProvider.OPENAI, None, "gpt-4o", "gpt-4o", False),
        (
            ModelProvider.OPENAI,
            "http://127.0.0.1:9/v1/",
            "team/exact/alias",
            "gpt-4o",
            True,
        ),
        (
            ModelProvider.AZURE,
            "http://127.0.0.1:9/",
            "deployment-alias",
            "gpt-4o",
            True,
        ),
        (
            ModelProvider.AZURE,
            "http://127.0.0.1:9/",
            "deployment-alias",
            "not-in-catalog",
            False,
        ),
    ],
)
def test_guardrail_catalog_and_alias_selection(
    judge_store, monkeypatch, provider, endpoint, model, base_model, accepted
):
    sessions, _ = judge_store
    configure_provider(sessions, provider=provider, endpoint=endpoint)
    monkeypatch.setattr(
        ModelProviderRepository,
        "list_catalog_models_for_provider",
        lambda *args: ["gpt-4o"],
    )
    with sessions() as session:
        repository = ModelProviderRepository(session)
        repository.set_model_whitelist(provider, [])
        selection = GuardrailLLMConfiguration(
            provider=provider, model=model, base_model=base_model
        )
        if accepted:
            configuration_service.validate_guardrail_selection(session, selection)
        else:
            with pytest.raises(HTTPException):
                configuration_service.validate_guardrail_selection(session, selection)


def test_transport_settings_and_rate_defaults(judge_store, monkeypatch):
    sessions, org_id = judge_store
    configure_provider(
        sessions, model="unknown/alias", endpoint="http://127.0.0.1:9/v1/"
    )
    context = configuration_service.capture_judge_context(org_id)
    try:
        assert context.limiter.token_limit == 20000
        assert context.limiter.period_seconds == 60
        assert context.structured_output is False
        assert context.input_limit > 0
    finally:
        context.close()
    monkeypatch.setenv("GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS", "0")
    assert (
        configuration_service.capture_judge_context(org_id).error
        == CONFIGURATION_UNAVAILABLE
    )
    with pytest.raises(ValidationError):
        GuardrailRateSettings()


def test_partial_failure_retains_usage_and_records_audit_once(monkeypatch):
    handle = MagicMock()
    observed = LLMTokenConsumption(prompt_tokens=7, completion_tokens=3)

    def fail_after_usage(messages, response_format, observe, started):
        started()
        observe(observed)
        raise ValueError("untrusted provider response")

    handle.invoke.side_effect = fail_after_usage
    record = MagicMock()
    monkeypatch.setattr(
        "services.guardrails.judge_executor.record_model_invocation", record
    )
    evaluation = JudgeEvaluation(
        JudgeContext(
            org_id=uuid4(), provider=ModelProvider.OPENAI, model="gpt-4o", handle=handle
        )
    )
    with pytest.raises(ValueError) as raised:
        evaluation.complete([HumanMessage(content="test")], "sensitive data check")
    result = evaluation.unavailable(raised.value)
    assert result.result == RuleResultEnum.UNAVAILABLE
    assert result.prompt_tokens == 7
    assert result.completion_tokens == 3
    assert "untrusted" not in result.details.message
    invocation = record.call_args.args[0]
    assert invocation.success is False
    assert invocation.total_tokens == 10
    record.assert_called_once()


def test_quota_rejection_is_not_a_physical_invocation(monkeypatch):
    handle = MagicMock()
    handle.invoke.side_effect = HTTPException(
        429, detail={"error_code": "TOKEN_LIMIT_EXCEEDED", "message": "Credit limit"}
    )
    record = MagicMock()
    monkeypatch.setattr(
        "services.guardrails.judge_executor.record_model_invocation", record
    )
    evaluation = JudgeEvaluation(
        JudgeContext(
            org_id=uuid4(),
            model="gpt-4o",
            handle=handle,
            limiter=JudgeRateLimiter(20000, 60),
        )
    )
    with pytest.raises(HTTPException) as raised:
        evaluation.complete([HumanMessage(content="test")], "sensitive data check")
    assert evaluation.unavailable(raised.value).details.message == "Credit limit"
    record.assert_not_called()
    assert not evaluation.context.limiter.calls


def test_sensitive_examples_are_request_local():
    scorer = SensitiveDataCustomExamples()
    barrier = threading.Barrier(2)
    prompts = {}

    def run(marker):
        handle = MagicMock()

        def invoke(messages, response_format, observe, started):
            started()
            barrier.wait(timeout=5)
            prompts[marker] = messages[0].content
            observe(LLMTokenConsumption(prompt_tokens=2, completion_tokens=1))
            return JudgeCallResult(
                "yes" if marker == "alpha" else "no", None, zero_tokens()
            )

        handle.invoke.side_effect = invoke
        request = ScoreRequest(
            rule_type=RuleType.MODEL_SENSITIVE_DATA,
            user_prompt=f"{marker}-prompt",
            hint=f"{marker}-hint",
            examples=[
                Example(
                    exampleInput=f"{marker}-example",
                    ruleOutput=RuleScore(result=RuleResultEnum.FAIL),
                )
            ],
        )
        return scorer.score(
            request, JudgeContext(org_id=uuid4(), model="gpt-4o", handle=handle)
        )

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(run, ["alpha", "beta"]))
    assert [result.result for result in results] == [
        RuleResultEnum.FAIL,
        RuleResultEnum.PASS,
    ]
    assert "alpha-hint" in prompts["alpha"] and "beta" not in prompts["alpha"]
    assert "beta-example" in prompts["beta"] and "alpha" not in prompts["beta"]
    assert [result.prompt_tokens for result in results] == [2, 2]


def test_selected_model_window_and_input_short_circuits(monkeypatch):
    scorer = MagicMock()
    scorer.score.return_value = RuleScore(result=RuleResultEnum.PASS)
    resolver = MagicMock(return_value=JudgeContext(org_id=uuid4(), input_limit=500))
    monkeypatch.setattr(
        "services.guardrails.validation.capture_judge_context", resolver
    )
    monkeypatch.setattr("rules_engine.MAX_HALLUCINATION_TOKEN_LIMIT", 10)
    monkeypatch.setattr("rules_engine.TokenCounter.count", lambda *args: 20)
    rule = Rule._from_request_model(
        NewRuleRequest(
            name="hallucination",
            type=RuleType.MODEL_HALLUCINATION_V2,
            apply_to_prompt=False,
            apply_to_response=True,
        ),
        scope=RuleScope.TASK,
    )
    request = ValidationRequest(prompt="prompt", response="claim", context="context")
    assert (
        evaluate_guardrails(request, [rule], scorer, uuid4())[
            0
        ].rule_score_result.result
        == RuleResultEnum.PASS
    )
    resolver.assert_called_once()
    scorer.score.assert_called_once()
    resolver.return_value = JudgeContext(org_id=uuid4(), input_limit=19)
    scorer.reset_mock()
    assert (
        evaluate_guardrails(request, [rule], scorer, uuid4())[
            0
        ].rule_score_result.result
        == RuleResultEnum.SKIPPED
    )
    scorer.score.assert_not_called()
    resolver.reset_mock()
    request.context = None
    assert (
        evaluate_guardrails(request, [rule], scorer, uuid4())[
            0
        ].rule_score_result.result
        == RuleResultEnum.SKIPPED
    )
    resolver.assert_not_called()
