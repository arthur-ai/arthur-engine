"""Every GraphQL document the Wiz connector sends, checked against Wiz's schema.

The schema is a pruned copy of one printed from live Wiz introspection
(`fixtures/wiz/wiz-schema.pruned.graphql`; its header names the source and commit). The
documents and variables are captured from a scan through the fake session, so a change
to what the connector sends is checked here without copying any query text. This checks
shape -- fields, arguments, variable and input types, enum values -- not live data.
"""

from pathlib import Path
from typing import Any, Callable

import pytest
from graphql import (
    GraphQLEnumType,
    OperationDefinitionNode,
    build_schema,
    get_variable_values,
    parse,
    validate,
)
from test_wiz_connector import (
    AWS_ACCOUNT,
    FIELDS,
    FakeSession,
    graph_body,
    node,
    page_body,
    pages,
    scan,
    sighting,
)

from discovery.cloud.wiz.client import AI_STACK_LAYER, WORKLOAD_ENTITY_TYPES
from discovery.cloud.wiz.connector import DEFAULT_ENTITY_TYPES

SCHEMA = build_schema(
    (
        Path(__file__).parent / "fixtures" / "wiz" / "wiz-schema.pruned.graphql"
    ).read_text(),
)
ENTITY_TYPE = SCHEMA.get_type("GraphEntityType")
assert isinstance(ENTITY_TYPE, GraphQLEnumType)
ENTITY_TYPES = set(ENTITY_TYPE.values)


def sent(session: FakeSession) -> list[dict[str, Any]]:
    """The GraphQL bodies the connector posted (the token request is form-encoded)."""
    bodies = [c["json"] for c in session.calls if "json" in c]
    assert bodies
    return bodies


def root_field(body: dict[str, Any]) -> str:
    return "hostedTechnologies" if "hostedTechnologies(" in body["query"] else "cloud"


def type_names(value: Any) -> list[str]:
    """Every name under a `type: {equals: [...]}` filter, at any depth."""
    if not isinstance(value, dict):
        return []
    found = list(value.get("type", {}).get("equals", []))
    for child in value.values():
        found += type_names(child)
    return found


def problems(body: dict[str, Any]) -> list[str]:
    doc = parse(body["query"])
    errors = validate(SCHEMA, doc)
    if errors:
        return [e.message for e in errors]
    (op,) = [d for d in doc.definitions if isinstance(d, OperationDefinitionNode)]
    variables = body["variables"]
    declared = {v.variable.name.value for v in op.variable_definitions}
    found = [f"undeclared variable ${n}" for n in sorted(set(variables) - declared)]
    coerced = get_variable_values(SCHEMA, op.variable_definitions, variables)
    if isinstance(coerced, list):
        found += [e.message for e in coerced]
    found += [
        f"{name} is not a GraphEntityType"
        for name in type_names(variables.get("filterBy"))
        if name not in ENTITY_TYPES
    ]
    return found


def assert_valid(bodies: list[dict[str, Any]]) -> None:
    assert {root_field(b) for b in bodies} == {"cloud", "hostedTechnologies"}
    for body in bodies:
        assert problems(body) == [], body["query"].splitlines()[0]


def scanned(session: FakeSession, **kw: Any) -> list[dict[str, Any]]:
    scan(session, **kw)
    bodies = sent(session)
    assert_valid(bodies)
    return bodies


def only(bodies: list[dict[str, Any]], root: str) -> list[dict[str, Any]]:
    return [b for b in bodies if root_field(b) == root]


def test_the_default_entity_types_match_wizs_schema() -> None:
    (cloud,) = only(scanned(FakeSession()), "cloud")
    assert type_names(cloud["variables"]["filterBy"]) == list(DEFAULT_ENTITY_TYPES)


def test_an_entity_types_override_matches_wizs_schema() -> None:
    fields = {**FIELDS, "entity_types": "ai_model, MCP_SERVER, AI_DEPLOYMENT"}
    (cloud,) = only(scanned(FakeSession(), fields=fields), "cloud")
    assert type_names(cloud["variables"]["filterBy"]) == [
        "AI_MODEL",
        "MCP_SERVER",
        "AI_DEPLOYMENT",
    ]


def test_the_stack_layer_and_resource_type_filters_match_wizs_schema() -> None:
    (workload,) = only(scanned(FakeSession()), "hostedTechnologies")
    filter_by = workload["variables"]["filterBy"]
    assert filter_by["technologyV2"]["category"]["stackLayer"] == [AI_STACK_LAYER]
    assert filter_by["resource"]["type"]["equals"] == list(WORKLOAD_ENTITY_TYPES)


def test_a_paging_cursor_matches_wizs_schema() -> None:
    other = f"arn:aws:ec2:us-east-1:{AWS_ACCOUNT}:instance/i-0fff"
    session = FakeSession(
        pages(page_body([node("a")], has_next=True, cursor="c1"), page_body([])),
        workloads=pages(
            graph_body([sighting()], has_next=True, cursor="g1"),
            graph_body([sighting(provider_id=other)]),
        ),
    )
    bodies = scanned(session)
    afters = {
        root: [b["variables"].get("after") for b in only(bodies, root)]
        for root in ("cloud", "hostedTechnologies")
    }
    assert afters == {"cloud": [None, "c1"], "hostedTechnologies": [None, "g1"]}


def _misspell_field(body: dict[str, Any]) -> None:
    body["query"] = body["query"].replace("endCursor", "endCusor")


def _bad_stack_layer(body: dict[str, Any]) -> None:
    body["variables"]["filterBy"]["technologyV2"]["category"]["stackLayer"] = ["AI"]


def _bad_entity_type(body: dict[str, Any]) -> None:
    body["variables"]["filterBy"]["resource"]["type"]["equals"] = ["VIRTUAL_MACHINES"]


def _string_page_size(body: dict[str, Any]) -> None:
    body["variables"]["first"] = "500"


@pytest.mark.parametrize(
    ("break_it", "expected"),
    [
        (_misspell_field, "Cannot query field 'endCusor'"),
        (_bad_stack_layer, "Value 'AI' does not exist in 'TechnologyStackLayer'"),
        (_bad_entity_type, "VIRTUAL_MACHINES is not a GraphEntityType"),
        (_string_page_size, "Int cannot represent non-integer value: '500'"),
    ],
)
def test_the_check_catches_a_document_wiz_would_reject(
    break_it: Callable[[dict[str, Any]], None],
    expected: str,
) -> None:
    scan(session := FakeSession())
    (workload,) = only(sent(session), "hostedTechnologies")
    assert problems(workload) == []
    break_it(workload)
    assert any(expected in p for p in problems(workload)), problems(workload)
