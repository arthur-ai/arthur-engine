import uuid
from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import litellm
import pytest
from arthur_common.models.enums import RuleResultEnum
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from langchain_core.prompts import ChatPromptTemplate
from litellm.types.utils import Choices, Message, ModelResponse, Usage
from pydantic import BaseModel, SecretStr

from clients.llm.llm_client import LLMModelResponse
from monitoring.ai_activity import _model_invocations, get_recorded_invocations
from repositories.model_provider_repository import ModelProviderRepository
from rules_engine import MAX_HALLUCINATION_TOKEN_LIMIT, RuleEngine
from schemas.custom_exceptions import (
    LLMContentFilterException,
    LLMExecutionException,
    LLMMaxRequestTokensException,
)
from schemas.request_schemas import PutDefaultModelProvider
from scorer.checks.sensitive_data.custom_examples import SensitiveDataCustomExamples
from scorer.judge_model import (
    DefaultModelJudge,
    EnvJudge,
    env_model_is_placeholder,
    llm_checks_billed_to,
    resolve_judge,
)
from tests.clients.base_test_client import override_get_db_session
from tests.unit.test_sensitive_data import BASE_CASE_REQUEST
from utils.constants import DEFAULT_ORG_ID

# The default model provider and its credentials are instance-wide state
pytestmark = pytest.mark.xdist_group("default_model_provider")

PROMPT = ChatPromptTemplate.from_messages(
    [("system", "You judge {thing}."), ("human", "Is {thing} good?")],
)


class Verdict(BaseModel):
    good: bool


@contextmanager
def _test_db_session():
    session = override_get_db_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def anthropic_default():
    """Anthropic credentials and the default model, removed after the test."""
    db = override_get_db_session()
    repo = ModelProviderRepository(db)
    repo.clear_default_model_provider()
    repo.set_model_provider_credentials(
        ModelProvider.ANTHROPIC,
        api_key=SecretStr("test-key"),
    )
    repo.set_default_model_provider(
        PutDefaultModelProvider(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-opus-5-5",
        ),
    )
    with patch("dependencies.db_session_context", _test_db_session):
        yield repo
    repo.clear_default_model_provider()
    repo.delete_model_provider_credentials(ModelProvider.ANTHROPIC)
    db.close()


@pytest.fixture
def env_configured():
    executor = MagicMock()
    executor.gpt_hosts = "gpt-4o::https://example.openai.azure.com/::real-key"
    executor.get_gpt_model.return_value = MagicMock(model_name="gpt-4o")
    with patch("scorer.judge_model.get_llm_executor", return_value=executor):
        yield executor


@pytest.fixture
def env_not_configured():
    # Settings validation fails when the env model variable isn't set at all
    with patch(
        "scorer.judge_model.get_llm_executor",
        side_effect=ValueError("GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS"),
    ):
        yield


@pytest.fixture
def no_default():
    db = override_get_db_session()
    ModelProviderRepository(db).clear_default_model_provider()
    with patch("dependencies.db_session_context", _test_db_session):
        yield
    db.close()


@pytest.fixture
def model_invocations() -> Generator[None, None, None]:
    """Collect audit invocations for the test, and stop collecting afterwards."""
    token = _model_invocations.set([])
    yield
    _model_invocations.reset(token)


def _source(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("GENAI_ENGINE_LLM_CHECKS_MODEL_SOURCE", value)


@pytest.mark.unit_tests
def test_auto_prefers_the_env_model(monkeypatch, anthropic_default, env_configured):
    """An install whose checks run on the env model doesn't move when a default is set."""
    _source(monkeypatch, "auto")
    judge = resolve_judge()
    assert isinstance(judge, EnvJudge)
    assert judge.model_name == "gpt-4o"


@pytest.mark.unit_tests
def test_auto_uses_the_default_without_an_env_model(
    monkeypatch,
    anthropic_default,
    env_not_configured,
):
    _source(monkeypatch, "auto")
    judge = resolve_judge()
    assert isinstance(judge, DefaultModelJudge)
    assert (judge.provider, judge.model_name) == (
        ModelProvider.ANTHROPIC,
        "claude-opus-5-5",
    )


@pytest.mark.unit_tests
def test_nothing_configured(monkeypatch, no_default, env_not_configured):
    _source(monkeypatch, "auto")
    assert resolve_judge() is None


@pytest.mark.unit_tests
def test_default_without_credentials_is_not_used(
    monkeypatch,
    anthropic_default,
    env_not_configured,
):
    with patch.object(
        ModelProviderRepository,
        "get_model_provider_client",
        side_effect=HTTPException(400, "model provider anthropic is not configured"),
    ):
        _source(monkeypatch, "auto")
        assert resolve_judge() is None


@pytest.mark.unit_tests
def test_source_forces_a_path(monkeypatch, anthropic_default, env_configured):
    _source(monkeypatch, "default_model")
    assert isinstance(resolve_judge(), DefaultModelJudge)
    _source(monkeypatch, "env")
    assert isinstance(resolve_judge(), EnvJudge)


@pytest.mark.unit_tests
def test_a_changed_default_applies_without_a_restart(
    monkeypatch,
    anthropic_default,
    env_not_configured,
):
    _source(monkeypatch, "auto")
    assert resolve_judge().model_name == "claude-opus-5-5"
    anthropic_default.set_default_model_provider(
        PutDefaultModelProvider(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-sonnet-5-5",
        ),
    )
    assert resolve_judge().model_name == "claude-sonnet-5-5"


@pytest.mark.unit_tests
def test_default_judge_is_billed_to_the_org(
    monkeypatch,
    anthropic_default,
    env_not_configured,
):
    _source(monkeypatch, "auto")
    task_org = uuid.uuid4()
    with llm_checks_billed_to(task_org):
        assert resolve_judge().org_id == task_org
    # a taskless validation
    assert resolve_judge().org_id == DEFAULT_ORG_ID


def _response(content: str, parsed: BaseModel | None = None) -> LLMModelResponse:
    return LLMModelResponse(
        response=ModelResponse(
            choices=[Choices(message=Message(content=content, role="assistant"))],
            usage=Usage(prompt_tokens=30, completion_tokens=7, total_tokens=37),
        ),
        structured_output_response=parsed,
    )


def _judge(client: Mock) -> DefaultModelJudge:
    return DefaultModelJudge(
        client=client,
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-5-5",
        org_id=DEFAULT_ORG_ID,
    )


@pytest.mark.unit_tests
def test_default_judge_structured_call(model_invocations):
    client = Mock()
    client.completion.return_value = _response('{"good": true}', Verdict(good=True))

    verdict, tokens = _judge(client).structured(
        PROMPT,
        {"thing": "tea"},
        Verdict,
        "test check",
    )

    assert verdict == Verdict(good=True)
    assert (tokens.prompt_tokens, tokens.completion_tokens) == (30, 7)
    kwargs = client.completion.call_args.kwargs
    assert kwargs["model"] == "anthropic/claude-opus-5-5"
    assert kwargs["response_format"] is Verdict
    assert kwargs["org_id"] == DEFAULT_ORG_ID
    assert kwargs["messages"] == [
        {"role": "system", "content": "You judge tea."},
        {"role": "user", "content": "Is tea good?"},
    ]
    # current Claude models reject temperature
    assert "temperature" not in kwargs
    [invocation] = get_recorded_invocations()
    assert (invocation.provider, invocation.model_name, invocation.success) == (
        "anthropic",
        "claude-opus-5-5",
        True,
    )
    assert invocation.total_tokens == 37


@pytest.mark.unit_tests
def test_default_judge_text_call():
    client = Mock()
    client.completion.return_value = _response("yes")

    text, _ = _judge(client).text(PROMPT, {"thing": "tea"}, "test check")

    assert text == "yes"
    assert "response_format" not in client.completion.call_args.kwargs


def _wrapped(provider_error: Exception) -> HTTPException:
    """An error raised the way LLMClient raises it: an HTTPException inside except."""
    try:
        raise provider_error
    except Exception:
        try:
            raise HTTPException(status_code=400, detail="Bad request to provider")
        except HTTPException as e:
            return e


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("raised", "expected", "message"),
    [
        (
            _wrapped(
                litellm.ContextWindowExceededError(
                    message="too long",
                    model="claude-opus-5-5",
                    llm_provider="anthropic",
                ),
            ),
            LLMMaxRequestTokensException,
            "max request token",
        ),
        (
            _wrapped(
                litellm.RateLimitError(
                    message="slow down",
                    llm_provider="anthropic",
                    model="claude-opus-5-5",
                ),
            ),
            LLMExecutionException,
            "rate limit",
        ),
        (
            _wrapped(
                litellm.ContentPolicyViolationError(
                    message="blocked",
                    model="claude-opus-5-5",
                    llm_provider="anthropic",
                ),
            ),
            LLMContentFilterException,
            "content policy",
        ),
        (
            HTTPException(status_code=401, detail="Authentication failed"),
            LLMExecutionException,
            "Authentication failed",
        ),
    ],
)
def test_default_judge_errors_leave_the_rule_unavailable(
    raised,
    expected,
    message,
    model_invocations,
):
    client = Mock()
    client.completion.side_effect = raised

    with pytest.raises(expected) as exc_info:
        _judge(client).text(PROMPT, {"thing": "tea"}, "test check")

    assert message in str(exc_info.value)
    [invocation] = get_recorded_invocations()
    assert invocation.success is False
    assert invocation.error_type is not None


@pytest.mark.unit_tests
def test_a_check_runs_on_the_default_model():
    client = Mock()
    client.completion.return_value = _response("yes")
    with patch(
        "scorer.checks.sensitive_data.custom_examples.resolve_judge",
        return_value=_judge(client),
    ):
        score = SensitiveDataCustomExamples().score(BASE_CASE_REQUEST)

    assert score.result == RuleResultEnum.FAIL
    assert (score.prompt_tokens, score.completion_tokens) == (30, 7)


@pytest.mark.unit_tests
def test_a_check_with_no_model_is_unavailable():
    with patch(
        "scorer.checks.sensitive_data.custom_examples.resolve_judge",
        return_value=None,
    ):
        score = SensitiveDataCustomExamples().score(BASE_CASE_REQUEST)

    assert score.result == RuleResultEnum.UNAVAILABLE


@pytest.mark.unit_tests
def test_hallucination_token_limit_follows_the_judge():
    judge = Mock()
    judge.max_input_tokens.return_value = 50_000
    with patch("rules_engine.resolve_judge", return_value=judge):
        assert RuleEngine(Mock()).hallucination_token_limit == 50_000
    with patch("rules_engine.resolve_judge", return_value=None):
        assert (
            RuleEngine(Mock()).hallucination_token_limit
            == MAX_HALLUCINATION_TOKEN_LIMIT
        )


@pytest.mark.unit_tests
def test_default_judge_reads_the_input_window():
    judge = _judge(Mock())
    assert judge.max_input_tokens() == 1_000_000
    unknown = DefaultModelJudge(
        Mock(), ModelProvider.OPENAI, "not-a-model", DEFAULT_ORG_ID
    )
    assert unknown.max_input_tokens() is None


@pytest.mark.unit_tests
def test_env_judge_needs_a_model():
    executor = MagicMock()
    executor.get_gpt_model.return_value = None
    with pytest.raises(ValueError):
        EnvJudge(executor, 0.0)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("value", "placeholder"),
    [
        ("model_name::::my_api_key", True),
        ("model_name::https://model_service.com/::my_api_key", True),
        ("", True),
        (None, True),
        ("gpt-4o::https://example.openai.azure.com/::real-key", False),
        ("model_name::::my_api_key,gpt-4o::::real-key", False),
    ],
)
def test_env_model_placeholders(value, placeholder):
    assert env_model_is_placeholder(value) is placeholder


@pytest.mark.unit_tests
def test_auto_ignores_a_placeholder_env_model(monkeypatch, anthropic_default):
    """The templates' placeholder must not hide the default model."""
    executor = MagicMock()
    executor.gpt_hosts = "model_name::::my_api_key"
    with patch("scorer.judge_model.get_llm_executor", return_value=executor):
        _source(monkeypatch, "auto")
        assert isinstance(resolve_judge(), DefaultModelJudge)


@pytest.mark.unit_tests
@pytest.mark.parametrize("content", ["", None])
def test_default_judge_rejects_an_empty_reply(content, model_invocations):
    """An empty reply would otherwise pass sensitive data, which looks for "yes"."""
    client = Mock()
    client.completion.return_value = _response(content)

    with pytest.raises(LLMExecutionException, match="no answer"):
        _judge(client).text(PROMPT, {"thing": "tea"}, "test check")

    [invocation] = get_recorded_invocations()
    assert invocation.success is False
    assert invocation.total_tokens == 37


@pytest.mark.unit_tests
def test_default_judge_audits_a_missing_structured_result(model_invocations):
    client = Mock()
    client.completion.return_value = _response('{"bad": 1}', None)

    with pytest.raises(LLMExecutionException, match="expected format"):
        _judge(client).structured(PROMPT, {"thing": "tea"}, Verdict, "test check")

    [invocation] = get_recorded_invocations()
    assert (invocation.success, invocation.error_type) == (
        False,
        "LLMExecutionException",
    )
    assert invocation.total_tokens == 37


@pytest.mark.unit_tests
def test_response_validation_bills_the_inferences_task():
    """The chat route validates responses without a task_id; billing still follows the
    task the inference belongs to."""
    from validation import response as response_validation

    inference = Mock(task_id="task-123", user_id=None, conversation_id=None)
    billed = []

    @contextmanager
    def capture(org_id):
        billed.append(org_id)
        yield

    @contextmanager
    def no_span(*args, **kwargs):
        yield Mock()

    with (
        patch.object(response_validation, "InferenceRepository") as repo,
        patch.object(response_validation, "guardrail_span", no_span),
        patch.object(response_validation, "RuleEngine"),
        patch.object(
            response_validation,
            "task_org_id",
            side_effect=lambda db, task_id: f"org-of-{task_id}",
        ),
        patch.object(response_validation, "llm_checks_billed_to", capture),
    ):
        repo.return_value.get_inference.return_value = inference
        try:
            response_validation.validate_response(
                inference_id="inference-1",
                body=Mock(response="hi", context=None, model_name=None),
                db_session=Mock(),
                scorer_client=Mock(),
                rules=[],
            )
        except Exception:
            pass  # only the billing org matters here

    assert billed == ["org-of-task-123"]
