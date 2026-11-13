"""Rebuild `wiz-schema.pruned.graphql` from a full Wiz SDL.

    git clone https://github.com/ArcavenAE/stave /tmp/stave
    cd ml-engine && uv run python tests/unit/discovery/fixtures/wiz/prune_wiz_schema.py \\
      /tmp/stave

Keeps the subset of the schema the connector's `*_QUERY` documents touch: each output
type with only the fields selected from it (every argument kept), and the full
definition of every input object, enum and scalar reachable from those arguments and the
operations' variables. A document valid against the subset is valid against the full
schema. Rerun whenever a query changes.
"""

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

from graphql import (
    DirectiveNode,
    DocumentNode,
    GraphQLSchema,
    InputObjectTypeDefinitionNode,
    InterfaceTypeDefinitionNode,
    NamedTypeNode,
    ObjectTypeDefinitionNode,
    TypeInfo,
    TypeInfoVisitor,
    UnionTypeDefinitionNode,
    Visitor,
    build_ast_schema,
    parse,
    print_ast,
    specified_directives,
    visit,
)

HERE = Path(__file__).resolve().parent
OUT = HERE / "wiz-schema.pruned.graphql"
# Filters take entity types as the `GraphEntityTypeValue` scalar, which accepts any
# string; the enum is kept so the test can check the names the connector sends.
EXTRA_TYPES = ("GraphEntityType",)
SOURCE = "https://github.com/ArcavenAE/stave/blob/{commit}/spec/wiz-schema.graphql"


def queries() -> list[str]:
    src = HERE.parents[4] / "src"
    sys.path[:0] = [str(src / "ml_engine"), str(src)]
    from discovery.cloud.wiz import client

    return [v for k, v in vars(client).items() if k.endswith("_QUERY")]


def selected_fields(
    schema: GraphQLSchema,
    docs: Iterable[DocumentNode],
) -> set[tuple[str, str]]:
    used: set[tuple[str, str]] = set()
    info = TypeInfo(schema)

    class Collect(Visitor):
        def enter_field(self, node: Any, *_: Any) -> None:
            parent = info.get_parent_type()
            if parent is None or info.get_field_def() is None:
                raise SystemExit(f"{node.name.value} is not in the schema")
            used.add((parent.name, node.name.value))

    for doc in docs:
        visit(doc, TypeInfoVisitor(info, Collect()))
    return used


def type_names(node: Any) -> Iterable[str]:
    """Every named type an AST node mentions."""
    found: list[str] = []

    class Names(Visitor):
        def enter_named_type(self, n: NamedTypeNode, *_: Any) -> None:
            found.append(n.name.value)

    visit(node, Names())
    return found


def directive_names(node: Any) -> Iterable[str]:
    found: list[str] = []

    class Names(Visitor):
        def enter_directive(self, n: DirectiveNode, *_: Any) -> None:
            found.append(n.name.value)

    visit(node, Names())
    return found


def prune(sdl: str, docs: list[DocumentNode]) -> str:
    full = parse(sdl, no_location=True)
    schema = build_ast_schema(full, assume_valid=True, assume_valid_sdl=True)
    used = selected_fields(schema, docs)
    defs = {d.name.value: d for d in full.definitions if hasattr(d, "name") and d.name}

    kept: dict[str, Any] = {}
    pending = [parent for parent, _ in used] + list(EXTRA_TYPES)
    for doc in docs:
        pending.extend(type_names(doc))

    def field_subset(node: Any) -> Any:
        fields = tuple(
            f for f in node.fields if (node.name.value, f.name.value) in used
        )
        for f in fields:
            pending.extend(type_names(f))
        return node.__class__(
            **{
                **{k: getattr(node, k) for k in node.keys},
                "fields": fields,
                "interfaces": (),
            },
        )

    while pending:
        name = pending.pop()
        if name in kept or name not in defs:
            continue  # built-in scalars are not in the SDL
        node = defs[name]
        if isinstance(node, UnionTypeDefinitionNode):
            raise SystemExit(f"{name}: unions are not supported by this script")
        if isinstance(node, (ObjectTypeDefinitionNode, InterfaceTypeDefinitionNode)):
            kept[name] = field_subset(node)
        else:
            kept[name] = node
            if isinstance(node, InputObjectTypeDefinitionNode):
                pending.extend(type_names(node))

    builtin = {d.name for d in specified_directives}
    directives = {
        n for node in kept.values() for n in directive_names(node) if n not in builtin
    }
    extra = [
        d
        for d in full.definitions
        if d.kind == "directive_definition" and d.name.value in directives
    ]
    body = [print_ast(kept[name]) for name in sorted(kept)]
    body = [print_ast(d) for d in extra] + body
    return "schema {\n  query: Query\n}\n\n" + "\n\n".join(body) + "\n"


def header(sdl: bytes, commit: str, licence_text: str) -> str:
    licence = licence_text.strip().splitlines()
    return "\n".join(
        [
            "# Wiz GraphQL schema, pruned to what the Wiz discovery connector queries.",
            "#",
            f"# Source: {SOURCE.format(commit=commit)}",
            f"# sha256 of the source file: {hashlib.sha256(sdl).hexdigest()}",
            "# That file was printed from a live Wiz tenant's introspection and is",
            "# published under the MIT License, reproduced below. This subset keeps",
            "# only the fields the connector selects (with all their arguments) and",
            "# every input, enum and scalar those reach, plus GraphEntityType. Generated by",
            "# prune_wiz_schema.py next to this file; do not edit by hand.",
            "#",
            *[f"# {line}".rstrip() for line in licence],
            "",
            "",
        ],
    )


def main(argv: Optional[list[str]] = None) -> None:
    checkout = Path((argv or sys.argv[1:])[0])
    commit = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    raw = (checkout / "spec" / "wiz-schema.graphql").read_bytes()
    licence = (checkout / "LICENSE").read_text()
    docs = [parse(q) for q in queries()]
    OUT.write_text(header(raw, commit, licence) + prune(raw.decode(), docs))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
