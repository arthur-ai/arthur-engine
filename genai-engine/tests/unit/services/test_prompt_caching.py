import json

import httpx
import litellm
import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from openai import OpenAI

from services.prompt.prompt_caching import (
    apply_eval_prompt_caching,
    eval_prompt_cache_key,
    static_template_prefix,
)

RUBRIC = "Score 1 if the response answers the question, otherwise 0."


def _params(content: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": "system instructions"},
            {"role": "user", "content": content},
        ],
    }


def _joined_text(content: str | list[dict]) -> str:
    if isinstance(content, str):
        return content
    return "".join(block["text"] for block in content)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "template,expected",
    [
        ("Rubric text\n\nQuestion: {{ question }}", "Rubric text\n\nQuestion:"),
        ("Rubric\n{{- question }}", "Rubric"),
        ("Rubric {% if x %}{{ x }}{% endif %}", "Rubric"),
        ("Rubric {# note #} {{ x }}", "Rubric"),
        ("{{ question }} rubric", ""),
        ("No variables at all\n", "No variables at all"),
    ],
)
def test_static_template_prefix(template, expected):
    assert static_template_prefix(template) == expected


@pytest.mark.unit_tests
def test_eval_prompt_cache_key_is_stable_and_versioned():
    key = eval_prompt_cache_key("task-1", "relevance", 3)
    assert key == eval_prompt_cache_key("task-1", "relevance", 3)
    assert key != eval_prompt_cache_key("task-1", "relevance", 4)
    assert key != eval_prompt_cache_key("task-2", "relevance", 3)
    assert key.startswith("arthur-eval-")
    assert len(key) <= 64


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name",
    [
        (ModelProvider.ANTHROPIC, "claude-sonnet-4-5"),
        (ModelProvider.BEDROCK, "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
        (ModelProvider.VERTEX_AI, "claude-sonnet-4-5@20250929"),
    ],
)
def test_claude_gets_breakpoint_on_static_block_only(provider, model_name):
    instructions = RUBRIC + "\n\nResponse: {{ response }}"
    rendered = RUBRIC + "\n\nResponse: Paris is the capital of France."
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=provider,
        model_name=model_name,
        instructions=instructions,
        cache_key="key",
    )

    assert "prompt_cache_key" not in params
    assert params["messages"][0] == {
        "role": "system",
        "content": "system instructions",
    }
    static_block, variable_block = params["messages"][1]["content"]
    assert static_block == {
        "type": "text",
        "text": RUBRIC + "\n\nResponse:",
        "cache_control": {"type": "ephemeral"},
    }
    assert variable_block == {
        "type": "text",
        "text": " Paris is the capital of France.",
    }
    assert _joined_text(params["messages"][1]["content"]) == rendered


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name",
    [
        (ModelProvider.OPENAI, "gpt-4.1"),
        (ModelProvider.OPENAI, "gpt-5.5"),
        (ModelProvider.AZURE, "gpt-5.1"),
    ],
)
def test_pre_5_6_openai_gets_prompt_cache_key_and_retention(provider, model_name):
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=provider,
        model_name=model_name,
        instructions=RUBRIC + "\n\nResponse: {{ response }}",
        cache_key="key",
    )

    assert params["prompt_cache_key"] == "key"
    # sent in extra_body because litellm drops the top-level parameter
    assert params["extra_body"] == {"prompt_cache_retention": "24h"}
    assert "prompt_cache_options" not in params
    assert params["messages"] == _params(rendered)["messages"]


@pytest.mark.unit_tests
def test_pre_5_6_openai_without_listed_retention_gets_key_only():
    # litellm does not list prompt_cache_retention for gpt-4o on Azure
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=ModelProvider.AZURE,
        model_name="gpt-4o",
        instructions=RUBRIC + "\n\nResponse: {{ response }}",
        cache_key="key",
    )

    assert params == {**_params(rendered), "prompt_cache_key": "key"}


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name",
    [
        (ModelProvider.OPENAI, "gpt-5.6"),
        (ModelProvider.OPENAI, "gpt-5.6-luna"),
        (ModelProvider.OPENAI, "gpt-6.1-sol"),
        # not in litellm's model map: detected by version
        (ModelProvider.OPENAI, "gpt-6.2"),
        (ModelProvider.AZURE, "gpt-5.6"),
    ],
)
def test_openai_5_6_plus_gets_explicit_breakpoint_on_static_block_only(
    provider,
    model_name,
):
    instructions = RUBRIC + "\n\nResponse: {{ response }}"
    rendered = RUBRIC + "\n\nResponse: Paris is the capital of France."
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=provider,
        model_name=model_name,
        instructions=instructions,
        cache_key="key",
    )

    assert params["prompt_cache_options"] == {"mode": "explicit"}
    assert params["prompt_cache_key"] == "key"
    assert "extra_body" not in params
    static_block, variable_block = params["messages"][1]["content"]
    assert static_block == {
        "type": "text",
        "text": RUBRIC + "\n\nResponse:",
        "prompt_cache_breakpoint": {"mode": "explicit"},
    }
    assert variable_block == {
        "type": "text",
        "text": " Paris is the capital of France.",
    }
    assert "cache_control" not in str(params)
    assert _joined_text(params["messages"][1]["content"]) == rendered


@pytest.mark.unit_tests
def test_openai_5_6_plus_without_breakpoint_stays_in_explicit_mode():
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=ModelProvider.OPENAI,
        model_name="gpt-5.6",
        instructions=RUBRIC + "\n\nResponse: {{ response }}",
        cache_key="key",
        add_cache_breakpoint=False,
    )

    # explicit mode with no breakpoint keeps implicit caching from writing the trace
    assert params == {
        **_params(rendered),
        "prompt_cache_key": "key",
        "prompt_cache_options": {"mode": "explicit"},
    }


@pytest.mark.unit_tests
def test_claude_without_breakpoint_is_left_unchanged():
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5",
        instructions=RUBRIC + "\n\nResponse: {{ response }}",
        cache_key="key",
        add_cache_breakpoint=False,
    )

    assert params == _params(rendered)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "provider,model_name",
    [
        (ModelProvider.GEMINI, "gemini-2.5-flash"),
        (ModelProvider.VERTEX_AI, "gemini-2.5-flash"),
        (ModelProvider.BEDROCK, "amazon.nova-pro-v1:0"),
        (ModelProvider.BEDROCK, "anthropic.claude-3-haiku-20240307-v1:0"),
        (ModelProvider.VLLM, "meta-llama/Llama-3.1-8B-Instruct"),
    ],
)
def test_other_providers_are_left_unchanged(provider, model_name):
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=provider,
        model_name=model_name,
        instructions=RUBRIC + "\n\nResponse: {{ response }}",
        cache_key="key",
    )

    assert params == _params(rendered)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "instructions,rendered",
    [
        # template starts with a variable: no static rubric to cache
        ("{{ response }}\n\n" + RUBRIC, "Paris\n\n" + RUBRIC),
        # rendered text does not start with the literal prefix
        ("Rubric {{ response }}", "Something else entirely"),
        # variables rendered to whitespace only
        (RUBRIC + " {{ response }}", RUBRIC + " "),
    ],
)
def test_claude_without_usable_static_prefix_gets_no_breakpoint(
    instructions,
    rendered,
):
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5",
        instructions=instructions,
        cache_key="key",
    )

    assert params == _params(rendered)


@pytest.mark.unit_tests
@pytest.mark.parametrize("model_name", ["gpt-5.6", "gpt-4.1"])
def test_openai_cache_fields_survive_into_the_request_body(model_name):
    instructions = RUBRIC + "\n\nResponse: {{ response }}"
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)
    apply_eval_prompt_caching(
        params,
        provider=ModelProvider.OPENAI,
        model_name=model_name,
        instructions=instructions,
        cache_key="key",
    )

    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 0,
                "model": model_name,
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

    client = OpenAI(
        api_key="sk-test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    litellm.completion(model=model_name, api_key="sk-test", client=client, **params)

    (body,) = sent
    assert body["prompt_cache_key"] == "key"
    if model_name == "gpt-5.6":
        assert body["prompt_cache_options"] == {"mode": "explicit"}
        assert body["messages"][1]["content"][0]["prompt_cache_breakpoint"] == {
            "mode": "explicit",
        }
        assert "prompt_cache_breakpoint" not in body["messages"][1]["content"][1]
        assert "prompt_cache_retention" not in body
    else:
        assert body["prompt_cache_retention"] == "24h"
        assert body["messages"][1]["content"] == rendered
