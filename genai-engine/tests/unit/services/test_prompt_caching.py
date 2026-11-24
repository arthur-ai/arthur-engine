import json

import httpx
import litellm
import pytest
from arthur_common.models.llm_model_providers import ModelProvider
from openai import OpenAI

from services.onboarding.insight_prompts import (
    ONBOARDING_INSIGHT_SYSTEM_PROMPT,
    onboarding_insight_user_message,
)
from services.prompt.prompt_caching import (
    apply_conversation_caching,
    apply_eval_prompt_caching,
    apply_shared_prefix_caching,
    eval_prompt_cache_key,
    static_template_prefix,
    static_template_suffix,
    system_prompt_cache_key,
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
@pytest.mark.parametrize("model_name", ["gpt-4o", "gpt-5.1", "gpt-5.6", "gpt-6-sol"])
def test_azure_gets_prompt_cache_key_only(model_name):
    # explicit cache mode and retention are unverified on Azure
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=ModelProvider.AZURE,
        model_name=model_name,
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


TRACES = "FACTS\nt01: 3 tool calls\n\n[1] AGENT root\n  [2] TOOL fetch_url args=..."
CLAUDE_MODELS = [
    (ModelProvider.ANTHROPIC, "claude-sonnet-4-5"),
    (ModelProvider.BEDROCK, "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    (ModelProvider.VERTEX_AI, "claude-sonnet-4-5@20250929"),
]
UNSUPPORTED_MODELS = [
    (ModelProvider.GEMINI, "gemini-2.5-flash"),
    (ModelProvider.VERTEX_AI, "gemini-2.5-flash"),
    (ModelProvider.BEDROCK, "amazon.nova-pro-v1:0"),
    (ModelProvider.VLLM, "meta-llama/Llama-3.1-8B-Instruct"),
]


def _insight_templates(kind: str) -> list[str]:
    return [ONBOARDING_INSIGHT_SYSTEM_PROMPT, onboarding_insight_user_message(kind)]


def _insight_params(kind: str) -> dict:
    system, user = _insight_templates(kind)
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user.replace("{{ traces }}", TRACES)},
        ],
    }


def _apply_insight_caching(kind: str, provider, model_name) -> dict:
    params = _insight_params(kind)
    apply_shared_prefix_caching(
        params,
        provider=provider,
        model_name=model_name,
        templates=_insight_templates(kind),
        cache_key="insights",
    )
    return params


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "template,expected",
    [
        (
            "{{ traces }}\n\nInsight kind: x\nQuestion: y",
            "Insight kind: x\nQuestion: y",
        ),
        ("Head {{ a }} middle {{ b }} tail\n", "tail"),
        ("Head {% if a %}{{ a }}{% endif %}", ""),
        ("Head {{- a -}}\n  tail", "tail"),
        ("No variables at all", None),
    ],
)
def test_static_template_suffix(template, expected):
    assert static_template_suffix(template) == expected


@pytest.mark.unit_tests
def test_system_prompt_cache_key_is_stable_per_family():
    key = system_prompt_cache_key("onboarding_insight_")
    assert key == system_prompt_cache_key("onboarding_insight_")
    assert key != system_prompt_cache_key("__chatbot_prompt__")
    assert key.startswith("arthur-system-")
    assert len(key) <= 64


@pytest.mark.unit_tests
@pytest.mark.parametrize("provider,model_name", CLAUDE_MODELS)
def test_claude_insight_breakpoint_follows_the_rendered_traces(provider, model_name):
    params = _apply_insight_caching("internet_access", provider, model_name)

    system, user = params["messages"]
    assert system == _insight_params("internet_access")["messages"][0]
    head, tail = user["content"]
    assert head == {
        "type": "text",
        "text": TRACES + "\n\n",
        "cache_control": {"type": "ephemeral"},
    }
    assert tail["text"].startswith("Insight kind: internet_access")
    assert "cache_control" not in tail
    assert _joined_text(user["content"]) == (
        _insight_params("internet_access")["messages"][1]["content"]
    )
    assert "prompt_cache_key" not in params


@pytest.mark.unit_tests
@pytest.mark.parametrize("provider,model_name", CLAUDE_MODELS)
def test_claude_insight_prompts_share_everything_up_to_the_breakpoint(
    provider,
    model_name,
):
    # every insight prompt of a batch must write and read the same cached prefix
    first = _apply_insight_caching("internet_access", provider, model_name)
    second = _apply_insight_caching("tool_failures", provider, model_name)

    assert first["messages"][0] == second["messages"][0]
    assert first["messages"][1]["content"][0] == second["messages"][1]["content"][0]
    assert first["messages"][1]["content"][1] != second["messages"][1]["content"][1]


@pytest.mark.unit_tests
@pytest.mark.parametrize("model_name", ["gpt-4.1", "gpt-5.5"])
def test_pre_5_6_openai_insight_gets_family_key_and_unchanged_messages(model_name):
    params = _apply_insight_caching("user_facing", ModelProvider.OPENAI, model_name)

    assert params["prompt_cache_key"] == "insights"
    assert params["extra_body"] == {"prompt_cache_retention": "24h"}
    assert params["messages"] == _insight_params("user_facing")["messages"]


@pytest.mark.unit_tests
def test_openai_5_6_plus_insight_gets_explicit_breakpoint_after_the_traces():
    params = _apply_insight_caching("user_facing", ModelProvider.OPENAI, "gpt-5.6")

    assert params["prompt_cache_key"] == "insights"
    assert params["prompt_cache_options"] == {"mode": "explicit"}
    head, tail = params["messages"][1]["content"]
    assert head == {
        "type": "text",
        "text": TRACES + "\n\n",
        "prompt_cache_breakpoint": {"mode": "explicit"},
    }
    assert "prompt_cache_breakpoint" not in tail
    assert "cache_control" not in str(params)


@pytest.mark.unit_tests
def test_azure_insight_gets_family_key_only():
    params = _apply_insight_caching("user_facing", ModelProvider.AZURE, "gpt-4o")

    assert params == {**_insight_params("user_facing"), "prompt_cache_key": "insights"}


@pytest.mark.unit_tests
@pytest.mark.parametrize("provider,model_name", UNSUPPORTED_MODELS)
def test_shared_prefix_caching_is_a_no_op_for_other_providers(provider, model_name):
    params = _apply_insight_caching("heavy_model", provider, model_name)

    assert params == _insight_params("heavy_model")


@pytest.mark.unit_tests
def test_claude_prompt_without_variables_gets_breakpoint_on_its_system_message():
    params = {
        "messages": [
            {"role": "system", "content": "fixed instructions"},
            {"role": "user", "content": "fixed question"},
        ],
    }
    apply_shared_prefix_caching(
        params,
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5",
        templates=["fixed instructions", "fixed question"],
        cache_key="key",
    )

    assert params["messages"] == [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "fixed instructions",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
        },
        {"role": "user", "content": "fixed question"},
    ]


@pytest.mark.unit_tests
def test_claude_prompt_ending_in_a_variable_gets_breakpoint_on_that_message():
    params = {"messages": [{"role": "user", "content": "Question: " + TRACES}]}
    apply_shared_prefix_caching(
        params,
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5",
        templates=["Question: {{ traces }}"],
        cache_key="key",
    )

    (block,) = params["messages"][0]["content"]
    assert block["cache_control"] == {"type": "ephemeral"}
    assert block["text"] == "Question: " + TRACES


@pytest.mark.unit_tests
def test_claude_shared_prefix_skips_rendered_text_that_lost_the_template_tail():
    params = {"messages": [{"role": "user", "content": "something else"}]}
    apply_shared_prefix_caching(
        params,
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-5",
        templates=["{{ traces }}\n\nQuestion: why?"],
        cache_key="key",
    )

    assert params == {"messages": [{"role": "user", "content": "something else"}]}


def _conversation(iteration: int) -> list[dict]:
    """The chatbot's messages on each iteration of its tool loop."""
    messages = [
        {"role": "system", "content": "You are the Arthur assistant."},
        {"role": "user", "content": "find my evals"},
    ]
    if iteration >= 2:
        messages += [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "type": "function",
                        "function": {"name": "search", "arguments": "{}"},
                    },
                ],
            },
            {"role": "tool", "tool_call_id": "tc1", "content": "3 evals found"},
        ]
    return messages


def _breakpoints(messages: list[dict], marker: str) -> list[tuple[int, str]]:
    return [
        (i, block["text"])
        for i, message in enumerate(messages)
        if isinstance(message.get("content"), list)
        for block in message["content"]
        if marker in block
    ]


def _plain(messages: list[dict]) -> list[dict]:
    """Messages with breakpoints taken off: the bytes the provider caches."""
    return [
        {
            **message,
            "content": (
                _joined_text(message["content"])
                if isinstance(message.get("content"), list)
                else message.get("content")
            ),
        }
        for message in messages
    ]


@pytest.mark.unit_tests
@pytest.mark.parametrize("provider,model_name", CLAUDE_MODELS)
def test_claude_chatbot_iterations_read_the_previous_iterations_prefix(
    provider,
    model_name,
):
    requests = []
    for iteration in (1, 2):
        params = {"messages": _conversation(iteration)}
        apply_conversation_caching(
            params,
            provider=provider,
            model_name=model_name,
            cache_key="chatbot",
        )
        requests.append(params["messages"])
    first, second = requests

    assert _breakpoints(first, "cache_control") == [
        (0, "You are the Arthur assistant."),
        (1, "find my evals"),
    ]
    assert _breakpoints(second, "cache_control") == [
        (0, "You are the Arthur assistant."),
        (3, "3 evals found"),
    ]
    # the second request starts with every message the first one cached
    assert _plain(second)[: len(first)] == _plain(first)
    for messages in requests:
        assert len(_breakpoints(messages, "cache_control")) <= 4


@pytest.mark.unit_tests
def test_openai_5_6_plus_chatbot_gets_explicit_breakpoints():
    params = {"messages": _conversation(2)}
    apply_conversation_caching(
        params,
        provider=ModelProvider.OPENAI,
        model_name="gpt-5.6",
        cache_key="chatbot",
    )

    assert params["prompt_cache_key"] == "chatbot"
    assert params["prompt_cache_options"] == {"mode": "explicit"}
    assert _breakpoints(params["messages"], "prompt_cache_breakpoint") == [
        (0, "You are the Arthur assistant."),
        (3, "3 evals found"),
    ]


@pytest.mark.unit_tests
@pytest.mark.parametrize("provider,model_name", UNSUPPORTED_MODELS)
def test_conversation_caching_is_a_no_op_for_other_providers(provider, model_name):
    params = {"messages": _conversation(2)}
    apply_conversation_caching(
        params,
        provider=provider,
        model_name=model_name,
        cache_key="chatbot",
    )

    assert params == {"messages": _conversation(2)}
