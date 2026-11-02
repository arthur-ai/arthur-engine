import json
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx
import litellm
import pytest
from arthur_common.models.llm_model_providers import ModelProvider, ReasoningEffortEnum
from litellm.llms.custom_httpx.http_handler import HTTPHandler
from openai import OpenAI

from db_models.secret_storage_models import DatabaseSecretStorage
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.enums import SecretType
from schemas.llm_eval_schemas import Eval
from schemas.request_schemas import (
    PromptCompletionRequest,
    PutModelProviderEvalDefaults,
)
from schemas.response_schemas import ModelProviderEvalDefaults
from services.prompt.provider_eval_defaults import apply_provider_eval_defaults
from tests.clients.base_test_client import override_get_db_session


def _defaults(
    provider: ModelProvider,
    reasoning_effort: Optional[str] = None,
    thinking: Optional[dict[str, Any]] = None,
) -> ModelProviderEvalDefaults:
    return ModelProviderEvalDefaults.model_validate(
        {
            "provider": provider,
            "reasoning_effort": reasoning_effort,
            "thinking": thinking,
        },
    )


@pytest.mark.unit_tests
def test_no_defaults_leaves_config_identical():
    config = {"temperature": 0.5, "max_tokens": 100}
    apply_provider_eval_defaults(
        config,
        _defaults(ModelProvider.ANTHROPIC),
        "claude-haiku-4-5",
    )
    assert config == {"temperature": 0.5, "max_tokens": 100}


@pytest.mark.unit_tests
def test_provider_default_fills_unset_reasoning():
    config: dict[str, Any] = {"temperature": 0.5}
    apply_provider_eval_defaults(
        config,
        _defaults(ModelProvider.ANTHROPIC, thinking={"type": "disabled"}),
        "claude-haiku-4-5",
    )
    assert config == {"temperature": 0.5, "thinking": {"type": "disabled"}}


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "eval_config",
    [
        {"reasoning_effort": ReasoningEffortEnum.HIGH},
        {"reasoning_effort": "high"},
        {"thinking": {"type": "enabled", "budget_tokens": 2048}},
    ],
)
def test_eval_reasoning_setting_wins_over_both_defaults(eval_config):
    config = dict(eval_config)
    apply_provider_eval_defaults(
        config,
        _defaults(
            ModelProvider.ANTHROPIC,
            reasoning_effort="low",
            thinking={"type": "disabled"},
        ),
        "claude-sonnet-4-5",
    )
    # An eval that sets either setting gets neither default.
    assert config == eval_config


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "model_name,reasoning_effort,applied",
    [
        # gpt-5-mini takes minimal but not none; gpt-5.1 the reverse.
        ("gpt-5-mini", "minimal", True),
        ("gpt-5-mini", "none", False),
        ("gpt-5.1", "none", True),
        ("gpt-5.1", "minimal", False),
        ("gpt-5-mini", "low", True),
        # gpt-4o-mini takes no reasoning_effort at all.
        ("gpt-4o-mini", "low", False),
        # A provider-prefixed model name resolves like the bare one.
        ("openai/gpt-4o-mini", "low", False),
        ("openai/gpt-5-mini", "minimal", True),
        # litellm doesn't know this model, so the default is sent as configured.
        ("my-fine-tune", "low", True),
    ],
)
def test_reasoning_effort_default_only_applies_where_supported(
    model_name,
    reasoning_effort,
    applied,
):
    config: dict[str, Any] = {}
    apply_provider_eval_defaults(
        config,
        _defaults(ModelProvider.OPENAI, reasoning_effort=reasoning_effort),
        model_name,
    )
    if applied:
        assert config == {"reasoning_effort": ReasoningEffortEnum(reasoning_effort)}
    else:
        assert config == {}


@pytest.mark.unit_tests
def test_thinking_default_skipped_for_models_without_it():
    config: dict[str, Any] = {}
    apply_provider_eval_defaults(
        config,
        _defaults(ModelProvider.OPENAI, thinking={"type": "disabled"}),
        "gpt-5-mini",
    )
    assert config == {}


@pytest.fixture
def anthropic_provider():
    """An enabled anthropic provider row, removed after the test."""
    db_session = override_get_db_session()
    ModelProviderRepository(db_session).delete_model_provider_credentials(
        ModelProvider.ANTHROPIC,
    )
    row = DatabaseSecretStorage(
        id=str(uuid.uuid4()),
        name=ModelProvider.ANTHROPIC,
        value={"api_key": "test-key"},
        secret_type=SecretType.MODEL_PROVIDER,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(row)
    db_session.commit()
    yield row
    db_session.delete(row)
    db_session.commit()


def _eval(
    model_provider: ModelProvider,
    model_name: str,
    config: Optional[dict[str, Any]] = None,
) -> Eval:
    return Eval(
        name="judge",
        model_name=model_name,
        model_provider=model_provider,
        instructions="Is {{answer}} correct?",
        variables=["answer"],
        config=config,
        version=1,
        created_at=datetime.now(),
    )


def _completion_params(llm_eval: Eval) -> tuple[str, dict[str, Any]]:
    repo = LLMEvalsRepository(override_get_db_session())
    prompt = repo.from_llm_eval_to_agentic_prompt(llm_eval)
    return repo.chat_completion_service._get_completion_params(
        prompt,
        PromptCompletionRequest(stream=False, strict=False),
    )


def _set_defaults(provider: ModelProvider, **defaults: Any) -> None:
    ModelProviderRepository(override_get_db_session()).set_eval_defaults(
        provider,
        PutModelProviderEvalDefaults(**defaults),
    )


@pytest.mark.unit_tests
def test_eval_path_precedence(anthropic_provider):
    eval_without_reasoning = _eval(
        ModelProvider.ANTHROPIC,
        "claude-haiku-4-5",
        {"temperature": 0.0},
    )
    _, baseline = _completion_params(eval_without_reasoning)
    assert "thinking" not in baseline and "reasoning_effort" not in baseline

    # Defaults row present but empty: the request is unchanged.
    _set_defaults(ModelProvider.ANTHROPIC)
    stored = ModelProviderRepository(override_get_db_session())._get_provider_secret(
        ModelProvider.ANTHROPIC,
    )
    assert stored is not None and stored.llm_eval_defaults is None
    assert _completion_params(eval_without_reasoning)[1] == baseline

    # Provider default fills what the eval leaves unset.
    _set_defaults(ModelProvider.ANTHROPIC, thinking={"type": "disabled"})
    _, params = _completion_params(eval_without_reasoning)
    assert params == {**baseline, "thinking": {"type": "disabled"}}

    # The eval's own setting wins.
    eval_with_reasoning = _eval(
        ModelProvider.ANTHROPIC,
        "claude-haiku-4-5",
        {"temperature": 0.0, "reasoning_effort": "medium"},
    )
    _, params = _completion_params(eval_with_reasoning)
    assert params["reasoning_effort"] == "medium"
    assert "thinking" not in params

    # Another provider's defaults never apply.
    openai_eval = _eval(ModelProvider.OPENAI, "gpt-5-mini", {"temperature": 0.0})
    _, params = _completion_params(openai_eval)
    assert "thinking" not in params and "reasoning_effort" not in params


def _anthropic_request_body(params: dict[str, Any], model: str) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [{"type": "text", "text": "{}"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    litellm.completion(
        model=model,
        api_key="test-key",
        client=HTTPHandler(client=httpx.Client(transport=httpx.MockTransport(handler))),
        **params,
    )
    return captured


def _openai_request_body(params: dict[str, Any], model: str) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "{}"},
                        "finish_reason": "stop",
                    },
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    litellm.completion(
        model=model,
        api_key="test-key",
        client=OpenAI(
            api_key="test-key",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        ),
        **params,
    )
    return captured


@pytest.mark.unit_tests
def test_claude_disabled_thinking_wire_shape(anthropic_provider):
    llm_eval = _eval(ModelProvider.ANTHROPIC, "claude-haiku-4-5", {"max_tokens": 512})

    model, params = _completion_params(llm_eval)
    body = _anthropic_request_body(params, model)
    assert "thinking" not in body

    _set_defaults(ModelProvider.ANTHROPIC, thinking={"type": "disabled"})
    model, params = _completion_params(llm_eval)
    body = _anthropic_request_body(params, model)
    assert body["thinking"] == {"type": "disabled"}
    assert body["max_tokens"] == 512


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "reasoning_effort,expected_thinking",
    [
        ("none", None),
        ("low", {"type": "enabled", "budget_tokens": 1024}),
        ("medium", {"type": "enabled", "budget_tokens": 2048}),
        ("high", {"type": "enabled", "budget_tokens": 4096}),
    ],
)
def test_claude_reasoning_effort_wire_shape(
    anthropic_provider,
    reasoning_effort,
    expected_thinking,
):
    # Documents what litellm sends; claude-haiku-4-5 takes a thinking budget.
    _set_defaults(ModelProvider.ANTHROPIC, reasoning_effort=reasoning_effort)
    model, params = _completion_params(
        _eval(ModelProvider.ANTHROPIC, "claude-haiku-4-5"),
    )
    body = _anthropic_request_body(params, model)
    assert body.get("thinking") == expected_thinking


@pytest.mark.unit_tests
@pytest.mark.parametrize("reasoning_effort", ["minimal", "low", "medium", "high"])
def test_openai_reasoning_effort_wire_shape(reasoning_effort):
    llm_eval = _eval(
        ModelProvider.OPENAI,
        "gpt-5-mini",
        {"reasoning_effort": reasoning_effort},
    )
    model, params = _completion_params(llm_eval)
    body = _openai_request_body(params, model)
    assert body["reasoning_effort"] == reasoning_effort
