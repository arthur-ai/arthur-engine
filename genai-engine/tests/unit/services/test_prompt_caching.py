import pytest
from arthur_common.models.llm_model_providers import ModelProvider

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
@pytest.mark.parametrize("provider", [ModelProvider.OPENAI, ModelProvider.AZURE])
def test_openai_gets_prompt_cache_key_and_no_cache_control(provider):
    rendered = RUBRIC + "\n\nResponse: Paris"
    params = _params(rendered)

    apply_eval_prompt_caching(
        params,
        provider=provider,
        model_name="gpt-4o",
        instructions=RUBRIC + "\n\nResponse: {{ response }}",
        cache_key="key",
    )

    assert params["prompt_cache_key"] == "key"
    assert params["messages"] == _params(rendered)["messages"]


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
