"""
Guard against inline schemas whose generated model name collides with a component.

openapi-generator names an inline anyOf/oneOf property schema after its title.
When that name matches a component schema, the generated class overwrites the
component's class. A Union[ModelProvider, Literal["empty"]] field titled
"Model Provider" once replaced the ModelProvider enum in genai_client with an
anyOf wrapper, so every client response carrying a plain model_provider string
failed validation.
"""

import re

import pytest

# Same collision with the ToolChoice component, not yet fixed. Remove entries
# from this set as they are given distinct titles; never add to it.
_KNOWN_COLLISIONS = {
    "LLMConfigSettings.tool_choice",
    "LLMPromptRequestConfigSettings.tool_choice",
}


def _generated_model_name(title: str) -> str:
    return "".join(
        word[:1].upper() + word[1:] for word in re.split(r"[^0-9A-Za-z]+", title)
    )


def _is_generated_as_model(schema: dict) -> bool:
    for key in ("anyOf", "oneOf"):
        members = [m for m in schema.get(key, []) if m.get("type") != "null"]
        if len(members) > 1:
            return True
    return False


@pytest.mark.unit_tests
def test_inline_schema_titles_do_not_collide_with_components():
    from server import get_app_with_routes

    schemas = get_app_with_routes().openapi()["components"]["schemas"]

    assert "enum" in schemas["ModelProvider"]

    collisions = [
        f"{schema_name}.{prop_name} (title {prop['title']!r})"
        for schema_name, schema in schemas.items()
        for prop_name, prop in schema.get("properties", {}).items()
        if f"{schema_name}.{prop_name}" not in _KNOWN_COLLISIONS
        and "title" in prop
        and _is_generated_as_model(prop)
        and _generated_model_name(prop["title"]) in schemas
    ]
    assert not collisions, (
        "These inline anyOf/oneOf properties have a title that openapi-generator "
        "turns into an existing component's name, which overwrites that component "
        "in generated clients. Give each one a distinct Field(title=...):\n"
        + "\n".join(collisions)
    )
