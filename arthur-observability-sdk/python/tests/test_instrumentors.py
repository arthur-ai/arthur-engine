"""Consistency test for the optional framework instrumentors."""

import ast
import pathlib
import re
import tomllib

import pytest

pytestmark = pytest.mark.unit_tests

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_instrumentors_are_consistent():
    """Every instrument_* method must have a matching extra, 'all' entry, and README row.

    Adding an instrumentor touches four places that must agree (see
    arthur-observability-sdk/CLAUDE.md).  Parsed from source rather than imported
    so the optional packages need not be installed.
    """
    source = (PACKAGE_ROOT / "src" / "arthur_observability_sdk" / "arthur.py").read_text()
    arthur_cls = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef) and node.name == "Arthur"
    )
    # method name -> (package, extra_name) from the _instrument() call
    methods = {
        node.name: [arg.value for arg in node.body[0].value.args][:2]
        for node in arthur_cls.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("instrument_")
    }

    pyproject = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
    extras = {
        extra: [requirement.split(";")[0].strip() for requirement in requirements]
        for extra, requirements in pyproject["project"]["optional-dependencies"].items()
    }
    documented = dict(
        re.findall(
            r"^\|\s*`([a-z0-9-]+)`\s*\|[^|]*\|\s*`(instrument_[a-z0-9_]+)\(\)`\s*\|$",
            (PACKAGE_ROOT / "README.md").read_text(),
            re.MULTILINE,
        )
    )

    assert methods, "no instrument_* methods found in arthur.py"
    for method_name, (package, extra_name) in sorted(methods.items()):
        assert extras.get(extra_name) == [package], (
            f"{method_name}() names extra '{extra_name}' for '{package}', but "
            f"pyproject.toml declares {extras.get(extra_name)}"
        )
        assert package in extras["all"], f"'{package}' is missing from the 'all' extra"
        assert documented.get(extra_name) == method_name, (
            f"README table maps '{extra_name}' to {documented.get(extra_name)}, "
            f"expected {method_name}()"
        )

    exposed = {package for package, _ in methods.values()}
    assert set(extras["all"]) == exposed, (
        f"'all' extra is out of sync: only in 'all' "
        f"{sorted(set(extras['all']) - exposed)}, missing from 'all' "
        f"{sorted(exposed - set(extras['all']))}"
    )
    assert not set(documented) - set(extras), (
        f"README lists extras that pyproject.toml does not declare: "
        f"{sorted(set(documented) - set(extras))}"
    )
