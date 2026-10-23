import ipaddress
import json
import ssl
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from arthur_common.models.enums import APIKeysRolesEnum, RuleResultEnum, RuleType
from arthur_common.models.llm_model_providers import ModelProvider
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from db_models import (
    DatabaseInference,
    DatabaseOrganization,
    DatabasePromptRuleResult,
    DatabaseResponseRuleResult,
    DatabaseTask,
)
from db_models.base import Base
from dependencies import get_scorer_client
from monitoring.ai_activity import (
    begin_ai_activity,
    end_ai_activity,
    get_recorded_invocations,
)
from repositories.api_key_repository import ApiKeyRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.enums import ClaimClassifierResultEnum
from schemas.scorer_schemas import Example, RuleScore, ScoreRequest
from scorer.checks.hallucination.v2 import HallucinationClaimsV2
from scorer.checks.keyword.keyword import KeywordScorer
from scorer.checks.sensitive_data.custom_examples import SensitiveDataCustomExamples
from scorer.score import ScorerClient
from services.guardrails import llm_configuration_service as configuration_service
from tests.clients import base_test_client
from tests.clients.unit_test_client import get_genai_engine_test_client
from tests.unit.validation.test_guardrail_judge_configuration import (
    configure_provider,
    judge_store,
)
from utils.constants import DEFAULT_ORG_ID, SYSTEM_ORG_ID

pytestmark = pytest.mark.integration_tests


@pytest.fixture(scope="module", autouse=True)
def client():
    """This suite uses its own local provider, not the remote integration client."""
    yield None


def create_certificate(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    certificate_path = tmp_path / "provider-ca.pem"
    key_path = tmp_path / "provider-key.pem"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return certificate_path, key_path


@contextmanager
def provider_server(
    tmp_path,
    *,
    tls=False,
    malformed=False,
    status=200,
    error_code="invalid_api_key",
    responder=None,
):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, dict(self.headers), body))
            structured = body.get("response_format") is not None
            sensitive = "sets of outputs from an LLM" in str(body["messages"])
            content = (
                "invalid json"
                if malformed
                else (
                    json.dumps(
                        {
                            "results": [
                                {
                                    "claim_text": "The sky is blue.",
                                    "is_hallucination": False,
                                    "explanation": "grounded",
                                }
                            ]
                        }
                    )
                    if structured
                    else "no" if sensitive else "0"
                )
            )
            request_status = status
            if responder is not None:
                request_status, content = responder(body)
            response = (
                {
                    "id": "local-judge",
                    "object": "chat.completion",
                    "created": 1,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": content},
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 17,
                        "completion_tokens": 7,
                        "total_tokens": 24,
                    },
                }
                if request_status == 200
                else {
                    "error": {
                        "message": "private upstream detail",
                        "type": "invalid_request_error",
                        "code": error_code,
                    }
                }
            )
            encoded = json.dumps(response).encode()
            self.send_response(request_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    certificate_path = None
    if tls:
        certificate_path, key_path = create_certificate(tmp_path)
        policy = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        policy.load_cert_chain(certificate_path, key_path)
        server.socket = policy.wrap_socket(server.socket, server_side=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"{'https' if tls else 'http'}://127.0.0.1:{server.server_port}", requests, certificate_path
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


@pytest.fixture
def billing(judge_store, monkeypatch):
    sessions, org_id = judge_store

    @contextmanager
    def session_context():
        with sessions() as session:
            yield session

    monkeypatch.setattr(
        "repositories.organizations_repository.db_session_context", session_context
    )
    monkeypatch.setenv("AUDIT_LOG_INCLUDE_AI_ACTIVITY", "true")
    return sessions, org_id


def run_judges(org_id, monkeypatch):
    classifier = MagicMock(
        return_value={"pred_label_str": [ClaimClassifierResultEnum.CLAIM]}
    )
    monkeypatch.setattr(
        "scorer.checks.hallucination.v2.get_claim_classifier", lambda *args: classifier
    )
    context = configuration_service.capture_judge_context(org_id)
    token = begin_ai_activity()
    try:
        sensitive = SensitiveDataCustomExamples().score(
            ScoreRequest(
                rule_type=RuleType.MODEL_SENSITIVE_DATA,
                user_prompt="Public information",
                examples=[
                    Example(
                        exampleInput="A private password",
                        ruleOutput=RuleScore(result=RuleResultEnum.FAIL),
                    )
                ],
            ),
            context,
        )
        hallucination = HallucinationClaimsV2(None).score(
            ScoreRequest(
                rule_type=RuleType.MODEL_HALLUCINATION_V2,
                context="The sky is blue.",
                llm_response="The sky is blue.",
            ),
            judge_context=context,
        )
        return [sensitive, hallucination], list(get_recorded_invocations())
    finally:
        context.close()
        end_ai_activity(token)


@pytest.mark.parametrize(
    ("provider", "alias", "base_model"),
    [
        (ModelProvider.OPENAI, "gpt-4o", None),
        (ModelProvider.OPENAI, "team/exact/alias", None),
        (ModelProvider.OPENAI, "team/exact/alias", "gpt-4o"),
        (ModelProvider.AZURE, "deployment-alias", None),
        (ModelProvider.AZURE, "deployment-alias", "gpt-4o"),
    ],
)
def test_configured_provider_invokes_both_judges_without_judge_env(
    billing, monkeypatch, tmp_path, provider, alias, base_model
):
    sessions, org_id = billing
    with provider_server(tmp_path) as (endpoint, requests, _):
        configure_provider(
            sessions,
            provider=provider,
            model=alias,
            endpoint=endpoint
            + ("/proxy/v1/" if provider == ModelProvider.OPENAI else "/"),
            base_model=base_model,
        )
        results, invocations = run_judges(org_id, monkeypatch)
    assert [result.result for result in results] == [
        RuleResultEnum.PASS,
        RuleResultEnum.PASS,
    ]
    assert len(requests) == len(invocations) == 2
    assert all(
        invocation.model_name == alias and invocation.success
        for invocation in invocations
    )
    assert all(
        result.prompt_tokens == 17 and result.completion_tokens == 7
        for result in results
    )
    for path, headers, body in requests:
        assert body["model"] == alias
        if provider == ModelProvider.OPENAI:
            assert path == "/proxy/v1/chat/completions"
            assert headers["Authorization"] == "Bearer local-test-credential"
        else:
            assert path.startswith(
                "/openai/deployments/deployment-alias/chat/completions?"
            )
            assert "api-version=2025-02-01-preview" in path
            assert headers["api-key"] == "local-test-credential"
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 48


@pytest.mark.parametrize("provider", [ModelProvider.OPENAI, ModelProvider.AZURE])
@pytest.mark.parametrize(
    ("trust", "passes"),
    [
        ("private_ca", True),
        ("default", False),
        ("insecure", True),
        ("missing_ca", False),
    ],
)
def test_configured_provider_private_ca_tls_and_verification(
    billing, monkeypatch, tmp_path, provider, trust, passes
):
    sessions, org_id = billing
    fallback = MagicMock()
    monkeypatch.setattr(configuration_service, "_environment_context", fallback)
    with provider_server(tmp_path, tls=True) as (endpoint, requests, certificate):
        configure_provider(
            sessions,
            provider=provider,
            model="deployment-alias",
            endpoint=endpoint + "/",
        )
        if trust != "default":
            monkeypatch.setenv("GENAI_ENGINE_OPENAI_VERIFY_SSL", "false")
        if trust in ("private_ca", "missing_ca"):
            monkeypatch.setenv(
                "GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL",
                "https://cert.example.test/ca",
            )
            monkeypatch.setattr(
                "config.openai_config.OPENAI_PRIVATE_CERT_PATH",
                (
                    str(certificate)
                    if trust == "private_ca"
                    else str(tmp_path / "missing.pem")
                ),
            )
        results, invocations = run_judges(org_id, monkeypatch)
    assert all((result.result == RuleResultEnum.PASS) == passes for result in results)
    assert len(requests) == (2 if passes else 0)
    assert len(invocations) == (0 if trust == "missing_ca" else 2)
    fallback.assert_not_called()


@pytest.mark.parametrize("source", ["stored", "environment"])
def test_structured_parse_failure_preserves_real_usage(
    billing, monkeypatch, tmp_path, source
):
    sessions, org_id = billing
    with provider_server(tmp_path, malformed=True) as (endpoint, requests, _):
        if source == "stored":
            configure_provider(sessions, endpoint=endpoint + "/v1/")
        else:
            monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
            monkeypatch.setenv(
                "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
                f"gpt-4o::{endpoint}/v1/::local-env-credential",
            )
        results, invocations = run_judges(org_id, monkeypatch)
    assert results[1].result == RuleResultEnum.UNAVAILABLE
    assert results[1].prompt_tokens == 17
    assert results[1].completion_tokens == 7
    assert len(requests) == len(invocations) == 2
    assert invocations[1].success is False
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 48


@pytest.mark.parametrize(
    ("status", "error_code"),
    [
        (401, "invalid_api_key"),
        (429, "rate_limit_exceeded"),
        (500, "server_error"),
        (504, "gateway_timeout"),
        (404, "model_not_found"),
        (400, "content_filter"),
        (400, "context_length_exceeded"),
    ],
)
def test_configured_upstream_failure_never_uses_environment(
    billing, monkeypatch, tmp_path, caplog, status, error_code
):
    sessions, org_id = billing
    with (
        provider_server(tmp_path, status=status, error_code=error_code) as (
            endpoint,
            requests,
            _,
        ),
        provider_server(tmp_path) as (fallback_endpoint, fallback_requests, _),
    ):
        monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
        monkeypatch.setenv(
            "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
            f"gpt-4o::{fallback_endpoint}/v1/::local-env-credential",
        )
        configure_provider(sessions, endpoint=endpoint + "/v1/")
        results, invocations = run_judges(org_id, monkeypatch)
    assert all(result.result == RuleResultEnum.UNAVAILABLE for result in results)
    assert len(requests) == len(invocations) == 2
    assert not fallback_requests
    assert "private upstream detail" not in caplog.text
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 0


@pytest.mark.parametrize("provider", ["OpenAI", "Azure"])
@pytest.mark.parametrize("deleted_selection", [False, True])
def test_environment_judges_bill_real_usage_after_absent_selection_or_deleted_provider(
    billing, monkeypatch, tmp_path, provider, deleted_selection
):
    sessions, org_id = billing
    with provider_server(tmp_path) as (endpoint, requests, _):
        if deleted_selection:
            configure_provider(sessions, endpoint=endpoint + "/v1/")
            with sessions() as session:
                ModelProviderRepository(session).delete_model_provider_credentials(
                    ModelProvider.OPENAI
                )
        monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", provider)
        monkeypatch.setenv(
            "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
            f"gpt-4o::{endpoint}/v1/::local-env-credential",
        )
        results, invocations = run_judges(org_id, monkeypatch)
    assert [result.result for result in results] == [
        RuleResultEnum.PASS,
        RuleResultEnum.PASS,
    ]
    assert len(requests) == len(invocations) == 2
    assert all(invocation.total_tokens == 24 for invocation in invocations)
    assert all(
        result.prompt_tokens == 17 and result.completion_tokens == 7
        for result in results
    )
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 48


@pytest.mark.parametrize("source", ["stored", "environment"])
def test_quota_is_checked_before_each_physical_judge_call(
    billing, monkeypatch, tmp_path, source
):
    sessions, org_id = billing
    with sessions() as session:
        session.get(DatabaseOrganization, org_id).tokens_limit = 24
        session.commit()
    with provider_server(tmp_path) as (endpoint, requests, _):
        if source == "stored":
            configure_provider(sessions, endpoint=endpoint + "/v1/")
        else:
            monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
            monkeypatch.setenv(
                "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
                f"gpt-4o::{endpoint}/v1/::local-env-credential",
            )
        results, invocations = run_judges(org_id, monkeypatch)
    assert results[0].result == RuleResultEnum.PASS
    assert results[1].result == RuleResultEnum.UNAVAILABLE
    assert results[1].prompt_tokens == results[1].completion_tokens == 0
    assert len(requests) == len(invocations) == 1
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 24


@pytest.mark.parametrize("source", ["stored", "environment"])
@pytest.mark.parametrize("explanation_failure", [False, True])
def test_nested_hallucination_batches_bill_and_audit_each_physical_call_once(
    billing, monkeypatch, tmp_path, source, explanation_failure
):
    sessions, org_id = billing
    monkeypatch.setattr(
        "scorer.checks.hallucination.v2.get_claim_classifier",
        lambda *args: lambda texts: {
            "pred_label_str": [ClaimClassifierResultEnum.CLAIM] * len(texts)
        },
    )

    def respond(body):
        last_message = body["messages"][-1]["content"]
        if "Flagged Claim:" not in last_message:
            return 200, "1"
        if explanation_failure and "Grass" in last_message:
            return 500, ""
        return 200, "The claim is unsupported by the context."

    with provider_server(tmp_path, responder=respond) as (endpoint, requests, _):
        if source == "stored":
            configure_provider(
                sessions, model="judge-alias", endpoint=endpoint + "/v1/"
            )
        else:
            monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
            monkeypatch.setenv(
                "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
                f"judge-alias::{endpoint}/v1/::local-env-credential",
            )
        context = configuration_service.capture_judge_context(org_id)
        token = begin_ai_activity()
        try:
            result = HallucinationClaimsV2(None).score(
                ScoreRequest(
                    rule_type=RuleType.MODEL_HALLUCINATION_V2,
                    context="No evidence is available.",
                    llm_response="The sky is green. Grass is purple. Water is orange. Snow is black.",
                ),
                claims_batch_size=1,
                judge_context=context,
            )
            invocations = list(get_recorded_invocations())
        finally:
            context.close()
            end_ai_activity(token)
    assert result.result == (
        RuleResultEnum.UNAVAILABLE if explanation_failure else RuleResultEnum.FAIL
    )
    assert len(requests) == len(invocations) == 8
    assert sum(not invocation.success for invocation in invocations) == int(
        explanation_failure
    )
    successful_calls = 8 - int(explanation_failure)
    assert result.prompt_tokens == successful_calls * 17
    assert result.completion_tokens == successful_calls * 7
    with sessions() as session:
        assert (
            session.get(DatabaseOrganization, org_id).tokens_used
            == successful_calls * 24
        )


@pytest.mark.parametrize("source", ["stored", "environment"])
def test_interleaved_rotated_snapshots_keep_distinct_credentials_and_private_cas(
    billing, monkeypatch, tmp_path, source
):
    sessions, org_id = billing
    first_path, second_path = tmp_path / "first", tmp_path / "second"
    first_path.mkdir()
    second_path.mkdir()
    with (
        provider_server(first_path, tls=True) as (
            first_endpoint,
            first_requests,
            first_ca,
        ),
        provider_server(second_path, tls=True) as (
            second_endpoint,
            second_requests,
            second_ca,
        ),
    ):
        monkeypatch.setenv(
            "GENAI_ENGINE_OPENAI_PRIVATE_CERT_DOWNLOAD_URL",
            "https://cert.example.test/ca",
        )
        monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
        contexts = []
        try:
            for endpoint, certificate, credential, model in (
                (first_endpoint, first_ca, "first-test-credential", "first-alias"),
                (second_endpoint, second_ca, "second-test-credential", "second-alias"),
            ):
                monkeypatch.setattr(
                    "config.openai_config.OPENAI_PRIVATE_CERT_PATH", str(certificate)
                )
                if source == "stored":
                    configure_provider(
                        sessions,
                        model=model,
                        endpoint=endpoint + "/v1/",
                        api_key=credential,
                    )
                else:
                    monkeypatch.setenv(
                        "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
                        f"{model}::{endpoint}/v1/::{credential}",
                    )
                contexts.append(configuration_service.capture_judge_context(org_id))
            for context in contexts * 2:
                result = SensitiveDataCustomExamples().score(
                    ScoreRequest(
                        rule_type=RuleType.MODEL_SENSITIVE_DATA,
                        user_prompt="Public information",
                        examples=[
                            Example(
                                exampleInput="private",
                                ruleOutput=RuleScore(result=RuleResultEnum.FAIL),
                            )
                        ],
                    ),
                    context,
                )
                assert result.result == RuleResultEnum.PASS
        finally:
            for context in contexts:
                context.close()
    assert len(first_requests) == len(second_requests) == 2
    for requests, credential, model in (
        (first_requests, "first-test-credential", "first-alias"),
        (second_requests, "second-test-credential", "second-alias"),
    ):
        assert all(
            headers["Authorization"] == f"Bearer {credential}"
            and body["model"] == model
            for _, headers, body in requests
        )
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 96


@pytest.fixture
def route_store(billing, monkeypatch):
    sessions, org_id = billing
    engine = sessions.kw["bind"]
    Base.metadata.create_all(engine)
    with sessions() as session:
        session.add_all(
            [
                DatabaseOrganization(
                    id=DEFAULT_ORG_ID,
                    name="default",
                    created_at=datetime.now(),
                ),
                DatabaseOrganization(
                    id=SYSTEM_ORG_ID,
                    name="system",
                    is_system=True,
                    created_at=datetime.now(),
                ),
            ]
        )
        session.commit()
    monkeypatch.setattr(base_test_client, "DATABASE_ENGINE", engine)
    monkeypatch.setattr(base_test_client, "SYSTEM_TASK_INITIALIZED", False)
    monkeypatch.setattr(
        "scorer.checks.hallucination.v2.get_claim_classifier",
        lambda *args: lambda texts: {
            "pred_label_str": [ClaimClassifierResultEnum.CLAIM] * len(texts)
        },
    )
    scorer = ScorerClient(
        {
            RuleType.MODEL_SENSITIVE_DATA: SensitiveDataCustomExamples(),
            RuleType.MODEL_HALLUCINATION_V2: HallucinationClaimsV2(None),
            RuleType.KEYWORD: KeywordScorer(),
        }
    )
    monkeypatch.setitem(
        base_test_client.app.dependency_overrides, get_scorer_client, lambda: scorer
    )
    client = get_genai_engine_test_client()
    status, _ = client.create_rule("Sensitive data", RuleType.MODEL_SENSITIVE_DATA)
    assert status == 200
    status, _ = client.create_rule("Hallucination", RuleType.MODEL_HALLUCINATION_V2)
    assert status == 200
    tasks = []
    for _ in range(3):
        status, task = client.create_task()
        assert status == 200
        tasks.append(task.id)
    other_org_id = uuid4()
    with sessions() as session:
        session.add(
            DatabaseOrganization(
                id=other_org_id, name="other-tenant", created_at=datetime.now()
            )
        )
        for index, task_id in enumerate(tasks):
            session.get(DatabaseTask, task_id).org_id = (
                other_org_id if index == 2 else org_id
            )
        key = ApiKeyRepository(session).create_api_key(
            description="Tenant",
            roles=[APIKeysRolesEnum.TENANT_USER],
            org_id=org_id,
        )
        tenant_headers = {"Authorization": f"Bearer {key.key}"}
    yield client, sessions, org_id, other_org_id, tasks, tenant_headers
    client.base_client.close()


def persistence_counts(session):
    return tuple(
        session.query(model).count()
        for model in (
            DatabaseInference,
            DatabasePromptRuleResult,
            DatabaseResponseRuleResult,
        )
    )


@pytest.mark.parametrize("source", ["stored", "environment"])
@pytest.mark.parametrize("actor", ["admin", "tenant"])
def test_real_judge_route_matrix_preserves_ownership_billing_and_persistence(
    route_store, monkeypatch, tmp_path, source, actor
):
    client, sessions, org_id, other_org_id, tasks, tenant_headers = route_store
    headers = (
        client.authorized_user_api_key_headers if actor == "admin" else tenant_headers
    )
    task_id, sibling_task_id, other_task_id = tasks
    with provider_server(tmp_path) as (endpoint, requests, _):
        if source == "stored":
            configure_provider(sessions, endpoint=endpoint + "/v1/")
        else:
            monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
            monkeypatch.setenv(
                "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
                f"gpt-4o::{endpoint}/v1/::local-env-credential",
            )

        def post(path, body, authorization=headers):
            return client.base_client.post(
                "/api/v2" + path, json=body, headers=authorization
            )

        def prompt(path):
            response = post(path, {"prompt": "Public information"})
            assert response.status_code == 200
            assert (
                response.json()["rule_results"][0]["result"] == "Pass"
            ), response.json()
            return response.json()["inference_id"]

        def response(path):
            result = post(
                path,
                {
                    "response": "The sky is blue.",
                    "context": "The sky is blue.",
                    "model_name": "evaluated-model",
                },
            )
            assert result.status_code == 200
            assert result.json()["model_name"] == "evaluated-model"
            assert result.json()["rule_results"][0]["result"] == "Pass"

        if actor == "admin":
            default_id = prompt("/validate_prompt")
            response(f"/validate_response/{default_id}")
        else:
            assert post("/validate_prompt", {"prompt": "public"}).status_code == 403
        inference_id = prompt(f"/tasks/{task_id}/validate_prompt")
        response(f"/tasks/{task_id}/validate_response/{inference_id}")
        legacy_id = prompt(f"/tasks/{task_id}/validate_prompt")
        response(f"/validate_response/{legacy_id}")
        before_rejected = len(requests)
        for path, body, authorization, status in (
            ("/validate", {"checks": []}, {}, 401),
            (f"/tasks/{uuid4()}/validate_prompt", {"prompt": "public"}, headers, 404),
            (f"/validate_response/{uuid4()}", {"response": "public"}, headers, 404),
            (
                f"/tasks/{task_id}/validate_response/{uuid4()}",
                {"response": "public"},
                headers,
                404,
            ),
            (
                f"/tasks/{sibling_task_id}/validate_response/{inference_id}",
                {"response": "public"},
                headers,
                404,
            ),
            (
                f"/tasks/{other_task_id}/validate_prompt",
                {"prompt": "public"},
                tenant_headers,
                404,
            ),
        ):
            assert post(path, body, authorization).status_code == status
        assert len(requests) == before_rejected
        with sessions() as session:
            counts = persistence_counts(session)
        inline = post(
            "/validate",
            {
                "prompt": "Public information",
                "checks": [
                    {
                        "name": "Sensitive data",
                        "type": RuleType.MODEL_SENSITIVE_DATA.value,
                        "apply_to_prompt": True,
                        "apply_to_response": False,
                        "config": {
                            "examples": [{"example": "private", "result": True}]
                        },
                    }
                ],
            },
        )
        assert inline.status_code == 200
        assert inline.json()["results"][0]["result"] == "Pass"
    with sessions() as session:
        assert persistence_counts(session) == counts
        assert counts == ((3, 3, 3) if actor == "admin" else (2, 2, 2))
        assert session.get(DatabaseOrganization, org_id).tokens_used == (
            96 if actor == "admin" else 120
        )
        assert session.get(DatabaseOrganization, DEFAULT_ORG_ID).tokens_used == (
            72 if actor == "admin" else 0
        )
        assert session.get(DatabaseOrganization, other_org_id).tokens_used == 0
        for model in (DatabasePromptRuleResult, DatabaseResponseRuleResult):
            assert session.query(model).filter(
                model.org_id == SYSTEM_ORG_ID
            ).count() == int(actor == "admin")
            assert session.query(model).filter(model.org_id == org_id).count() == 2
            assert all(
                result.prompt_tokens == 17 and result.completion_tokens == 7
                for result in session.query(model).all()
            )
        assert all(
            inference.model_name == "evaluated-model"
            and inference.inference_response.model_name == "evaluated-model"
            for inference in session.query(DatabaseInference).all()
        )
    assert len(requests) == (7 if actor == "admin" else 5)


@pytest.mark.parametrize("source", ["stored", "environment"])
def test_real_judge_routes_reject_exhausted_quota_before_provider_io(
    route_store, monkeypatch, tmp_path, source
):
    client, sessions, org_id, _, tasks, tenant_headers = route_store
    with sessions() as session:
        session.get(DatabaseOrganization, org_id).tokens_limit = 0
        session.commit()
    with provider_server(tmp_path) as (endpoint, requests, _):
        if source == "stored":
            configure_provider(sessions, endpoint=endpoint + "/v1/")
        else:
            monkeypatch.setenv("GENAI_ENGINE_OPENAI_PROVIDER", "OpenAI")
            monkeypatch.setenv(
                "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS",
                f"gpt-4o::{endpoint}/v1/::local-env-credential",
            )
        result = client.base_client.post(
            f"/api/v2/tasks/{tasks[0]}/validate_prompt",
            json={"prompt": "Public information"},
            headers=tenant_headers,
        )
        assert result.status_code == 200
        assert result.json()["rule_results"][0]["result"] == "Unavailable"
        inline = client.base_client.post(
            "/api/v2/validate",
            headers=tenant_headers,
            json={
                "prompt": "Public information",
                "checks": [
                    {
                        "name": "Sensitive data",
                        "type": RuleType.MODEL_SENSITIVE_DATA.value,
                        "apply_to_prompt": True,
                        "apply_to_response": False,
                        "config": {
                            "examples": [{"example": "private", "result": True}]
                        },
                    },
                    {
                        "name": "Keyword",
                        "type": RuleType.KEYWORD.value,
                        "apply_to_prompt": True,
                        "apply_to_response": False,
                        "config": {"keywords": ["Public"]},
                    },
                ],
            },
        )
        assert inline.status_code == 200
        assert {item["name"]: item["result"] for item in inline.json()["results"]} == {
            "Sensitive data": "Unavailable",
            "Keyword": "Fail",
        }
        assert not requests
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 0
        rule_result = session.query(DatabasePromptRuleResult).one()
        assert rule_result.prompt_tokens == rule_result.completion_tokens == 0
