"""Bookkeeping checks for the optional framework instrumentors.

Adding an instrumentor touches four places that must agree (see
arthur-observability-sdk/CLAUDE.md): the ``instrument_*`` method in
``arthur.py``, the individual extra in ``pyproject.toml``, the ``all`` extra,
and the README table row.  These tests assert those four agree.

Scope, deliberately: this is a *metadata* check.  It reads declarations rather
than importing the optional packages, so it runs with no extras installed and
in milliseconds — but it therefore cannot tell whether a declared
``module_path``/``class_name`` resolves against the package actually published
on PyPI.  That is ``scripts/verify_instrumentor.py``, run per-extra by
``.github/workflows/arthur-observability-sdk-instrumentors.yml``.
"""

from __future__ import annotations

from typing import Dict, List

import pytest

pytest.importorskip("tomllib", reason="registry parsing needs Python 3.11+")

from instrumentor_registry import (  # noqa: E402  (import follows the version guard)
    KNOWN_BROKEN,
    Instrumentor,
    load_documented,
    load_extras,
    load_instrumentors,
    marker_of,
)

pytestmark = pytest.mark.unit_tests

INSTRUMENTORS: Dict[str, Instrumentor] = load_instrumentors()
EXTRAS: Dict[str, List[str]] = load_extras()
RAW_EXTRAS: Dict[str, List[str]] = load_extras(strip_markers=False)
DOCUMENTED: Dict[str, str] = load_documented()

# Parametrise so that -v names each instrumentor and one bad row does not mask
# the rest.
DECLARATIONS = pytest.mark.parametrize(
    "instrumentor",
    sorted(INSTRUMENTORS.values()),
    ids=lambda instrumentor: instrumentor.method,
)


def test_registry_is_not_empty():
    """Guards against a parser change that silently matches nothing."""
    assert INSTRUMENTORS, "no instrument_* declarations found in arthur.py"
    assert "all" in EXTRAS, "pyproject.toml declares no 'all' extra"


@DECLARATIONS
def test_method_declares_a_matching_individual_extra(instrumentor: Instrumentor):
    assert EXTRAS.get(instrumentor.extra) == [instrumentor.package], (
        f"{instrumentor.method}() names extra '{instrumentor.extra}' for "
        f"'{instrumentor.package}', but pyproject.toml declares "
        f"{EXTRAS.get(instrumentor.extra)}"
    )


@DECLARATIONS
def test_package_is_in_the_all_extra(instrumentor: Instrumentor):
    assert instrumentor.package in EXTRAS["all"], (
        f"'{instrumentor.package}' is missing from the 'all' extra, so "
        f"pip install arthur-observability-sdk[all] would not enable "
        f"{instrumentor.method}()"
    )


@DECLARATIONS
def test_all_extra_repeats_the_individual_marker(instrumentor: Instrumentor):
    """A marked requirement must carry the same marker inside ``all``.

    ``beeai`` is 3.11+ only.  Dropping its marker from ``all`` would make
    ``pip install arthur-observability-sdk[all]`` unresolvable on 3.10, which
    the SDK still supports.
    """
    individual = {
        requirement.split(";")[0].strip(): marker_of(requirement)
        for requirement in RAW_EXTRAS[instrumentor.extra]
    }
    within_all = {
        requirement.split(";")[0].strip(): marker_of(requirement)
        for requirement in RAW_EXTRAS["all"]
    }
    expected = individual.get(instrumentor.package, "")
    assert within_all.get(instrumentor.package) == expected, (
        f"'{instrumentor.package}' has marker {expected!r} in extra "
        f"'{instrumentor.extra}' but {within_all.get(instrumentor.package)!r} in 'all'"
    )


@DECLARATIONS
def test_method_has_a_readme_table_row(instrumentor: Instrumentor):
    assert DOCUMENTED.get(instrumentor.extra) == instrumentor.method, (
        f"README table maps '{instrumentor.extra}' to "
        f"{DOCUMENTED.get(instrumentor.extra)}, expected {instrumentor.method}()"
    )


def test_all_extra_has_no_unreachable_packages():
    """Nothing in ``all`` that no ``instrument_*`` method can reach."""
    exposed = {instrumentor.package for instrumentor in INSTRUMENTORS.values()}
    orphaned = sorted(set(EXTRAS["all"]) - exposed)
    assert (
        not orphaned
    ), f"'all' extra installs packages with no instrument_* method: {orphaned}"


def test_no_individual_extra_is_orphaned():
    """Every instrumentor extra is reachable from a method.

    Catches an extra left behind when a method is renamed or removed — the
    ``all``-extra check above cannot see it if the extra was also dropped
    from ``all``.
    """
    declared_extras = {instrumentor.extra for instrumentor in INSTRUMENTORS.values()}
    orphaned = sorted(set(DOCUMENTED) - declared_extras)
    assert (
        not orphaned
    ), f"README documents extras with no instrument_* method: {orphaned}"


def test_readme_documents_no_undeclared_extras():
    undeclared = sorted(set(DOCUMENTED) - set(EXTRAS))
    assert (
        not undeclared
    ), f"README lists extras that pyproject.toml does not declare: {undeclared}"


def test_known_broken_entries_name_real_methods():
    """Keeps ``KNOWN_BROKEN`` from outliving the methods it waives.

    A stale entry would silently exempt nothing, or worse, exempt a method that
    was renamed back into existence later.
    """
    stale = sorted(set(KNOWN_BROKEN) - set(INSTRUMENTORS))
    assert not stale, (
        f"KNOWN_BROKEN in scripts/instrumentor_registry.py names methods that "
        f"no longer exist: {stale}"
    )
