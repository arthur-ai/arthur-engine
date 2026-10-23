import ipaddress
import json
import ssl
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType
from arthur_common.models.llm_model_providers import ModelProvider
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from db_models import DatabaseOrganization
from monitoring.ai_activity import (
    begin_ai_activity,
    end_ai_activity,
    get_recorded_invocations,
)
from schemas.enums import ClaimClassifierResultEnum
from schemas.scorer_schemas import Example, RuleScore, ScoreRequest
from scorer.checks.hallucination.v2 import HallucinationClaimsV2
from scorer.checks.sensitive_data.custom_examples import SensitiveDataCustomExamples
from services.guardrails import llm_configuration_service as configuration_service
from tests.unit.validation.test_guardrail_judge_configuration import (
    configure_provider,
    judge_store,
)

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
def provider_server(tmp_path, *, tls=False, malformed=False, status=200):
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
                if status == 200
                else {
                    "error": {
                        "message": "private upstream detail",
                        "type": "invalid_request_error",
                        "code": "invalid_api_key",
                    }
                }
            )
            encoded = json.dumps(response).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

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


def test_structured_parse_failure_preserves_real_usage(billing, monkeypatch, tmp_path):
    sessions, org_id = billing
    with provider_server(tmp_path, malformed=True) as (endpoint, requests, _):
        configure_provider(sessions, endpoint=endpoint + "/v1/")
        results, invocations = run_judges(org_id, monkeypatch)
    assert results[1].result == RuleResultEnum.UNAVAILABLE
    assert results[1].prompt_tokens == 17
    assert results[1].completion_tokens == 7
    assert len(requests) == len(invocations) == 2
    assert invocations[1].success is False
    with sessions() as session:
        assert session.get(DatabaseOrganization, org_id).tokens_used == 48


def test_configured_auth_failure_never_uses_environment(
    billing, monkeypatch, tmp_path, caplog
):
    sessions, org_id = billing
    with (
        provider_server(tmp_path, status=401) as (endpoint, requests, _),
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
