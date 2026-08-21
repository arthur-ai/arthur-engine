#!/usr/bin/env python3
"""Parses the SDK's declared instrumentor registry out of source.

Adding an instrumentor touches four places that must agree (see
arthur-observability-sdk/CLAUDE.md): the ``instrument_*`` method in
``arthur.py``, the individual extra in ``pyproject.toml``, the ``all`` extra,
and the README table row.  This module reads all four declaratively — no
importing of the SDK or of the optional openinference packages — so it runs
with nothing but a stdlib Python 3.11+.

Used by:
  * ``python/tests/test_instrumentors.py`` — asserts the four places agree.
  * ``scripts/verify_instrumentor.py`` — checks a declaration against the
    package actually published on PyPI.
  * ``.github/workflows/arthur-observability-sdk-instrumentors.yml`` — builds
    its verification matrix from ``--json``.

Command line:
  python3 scripts/instrumentor_registry.py                    # table
  python3 scripts/instrumentor_registry.py --json             # matrix JSON
  python3 scripts/instrumentor_registry.py --json --changed-since origin/dev
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import tomllib
from typing import Dict, List, NamedTuple, Optional

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_PACKAGE_ROOT = SCRIPT_DIR.parent / "python"

# Files whose contents define the registry, relative to the package root.
ARTHUR_SOURCE = pathlib.Path("src") / "arthur_observability_sdk" / "arthur.py"
PYPROJECT = pathlib.Path("pyproject.toml")
README = pathlib.Path("README.md")

# Matches a README "Supported instrumentors" row: | `extra` | Name | `method()` |
README_ROW = re.compile(
    r"^\|\s*`([a-z0-9-]+)`\s*\|[^|]*\|\s*`(instrument_[a-z0-9_]+)\(\)`\s*\|",
    re.MULTILINE,
)

# openinference packages the SDK deliberately does not expose, keyed by the
# extra name they would have had.  Each shipped an extra and an instrument_*
# method that could not work; rather than leave a declaration that fails for
# every user who installs it, the declaration is gone and the reason is recorded
# here.  See UP-4874 for restoring them.
#
# This is an exclusion list, not a waiver: nothing here is declared anywhere, so
# verify_instrumentor.py never sees these and the workflow is green on a clean
# registry.  test_instrumentors.py holds the list to that — an entry must be
# absent from arthur.py, pyproject.toml and the README, so re-adding support
# forces its removal from here rather than leaving two sources of truth.
#
# Two groups:
#   * six packages that are not BaseInstrumentor packages at all: five ship an
#     OTel SpanProcessor and codex a session-JSONL forwarder.  A SpanProcessor
#     needs tracer_provider.add_span_processor(...), which Arthur has no code
#     path for — _instrument() only knows cls().instrument().  Supporting them
#     means a second method shape in arthur.py, not a corrected class name.
#   * monkai-agent — our declaration was right; the upstream package is broken.
UNSUPPORTED: Dict[str, str] = {
    "agent-framework": (
        "Package ships AgentFrameworkToOpenInferenceProcessor (a SpanProcessor); "
        "there is no BaseInstrumentor to instantiate."
    ),
    "strands-agents": (
        "Package ships StrandsAgentsToOpenInferenceProcessor (a SpanProcessor); "
        "there is no BaseInstrumentor to instantiate."
    ),
    "openlit": (
        "Package ships OpenInferenceSpanProcessor (a SpanProcessor); "
        "there is no BaseInstrumentor to instantiate."
    ),
    "openllmetry": (
        "Package ships OpenInferenceSpanProcessor (a SpanProcessor); "
        "there is no BaseInstrumentor to instantiate."
    ),
    "pydantic-ai": (
        "Package ships OpenInferenceSpanProcessor (a SpanProcessor); "
        "there is no BaseInstrumentor to instantiate."
    ),
    "codex": (
        "Package ships CodexJsonlForwarder / NativeOtlpInterceptor — a session "
        "JSONL forwarding model that fits neither the instrumentor nor the "
        "span-processor shape."
    ),
    # The one entry whose declaration was correct: the upstream package is broken.
    "monkai-agent": (
        "Declaration was correct, but monkai-agent 0.0.1 raises NameError on "
        "import ('MCPAgent' is not defined in its own base.py), so importing "
        "the instrumentor fails.  Nothing to fix on our side — the extra is "
        "excluded until there is an upstream release."
    ),
}

# The package name an excluded extra would install, by the same convention every
# declared extra follows.  Kept derived rather than listed so the two cannot drift.
UNSUPPORTED_PACKAGES: Dict[str, str] = {
    extra: f"openinference-instrumentation-{extra}" for extra in UNSUPPORTED
}


class Instrumentor(NamedTuple):
    """One ``instrument_*`` declaration, as written in ``arthur.py``."""

    method: str
    package: str  # PyPI distribution name
    extra: str  # key in [project.optional-dependencies]
    module_path: str  # importlib path
    class_name: str  # attribute looked up on the module


class RegistryError(Exception):
    """A declaration could not be parsed — usually an unexpected call shape."""


def _instrument_param_names(arthur_cls: ast.ClassDef) -> List[str]:
    """Positional parameter names of ``Arthur._instrument``, minus ``self``.

    Read from source rather than hardcoded so that reordering or renaming the
    parameters cannot silently change what this module thinks it is reading.
    """
    for node in arthur_cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_instrument":
            return [arg.arg for arg in node.args.args][1:]
    raise RegistryError("Arthur._instrument() not found in arthur.py")


def _parse_declaration(
    method: ast.FunctionDef,
    param_names: List[str],
) -> Instrumentor:
    """Pull the four declared strings out of a method's ``_instrument`` call.

    Searches the whole body rather than assuming ``body[0]``, so a docstring or
    a guard clause does not break parsing, and accepts positional or keyword
    arguments in any mix.
    """
    call = next(
        (
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_instrument"
        ),
        None,
    )
    if call is None:
        raise RegistryError(f"{method.name}() does not call self._instrument()")

    values: Dict[str, str] = {}
    for name, arg in zip(param_names, call.args):
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            raise RegistryError(
                f"{method.name}(): argument '{name}' is not a string literal — "
                f"the registry can only be read from literal declarations",
            )
        values[name] = arg.value
    for keyword in call.keywords:
        if keyword.arg is None:
            raise RegistryError(f"{method.name}(): **kwargs unpacking is not readable")
        if not (
            isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ):
            raise RegistryError(
                f"{method.name}(): keyword '{keyword.arg}' is not a string literal",
            )
        values[keyword.arg] = keyword.value.value

    missing = [name for name in param_names if name not in values]
    if missing:
        raise RegistryError(f"{method.name}(): could not read {', '.join(missing)}")

    return Instrumentor(
        method=method.name,
        package=values["package"],
        extra=values["extra_name"],
        module_path=values["module_path"],
        class_name=values["class_name"],
    )


def load_instrumentors(
    package_root: pathlib.Path = DEFAULT_PACKAGE_ROOT,
) -> Dict[str, Instrumentor]:
    """Every ``instrument_*`` declaration on ``Arthur``, keyed by method name."""
    tree = ast.parse((package_root / ARTHUR_SOURCE).read_text())
    arthur_cls = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "Arthur"
        ),
        None,
    )
    if arthur_cls is None:
        raise RegistryError("class Arthur not found in arthur.py")

    param_names = _instrument_param_names(arthur_cls)
    return {
        node.name: _parse_declaration(node, param_names)
        for node in arthur_cls.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("instrument_")
    }


def load_extras(
    package_root: pathlib.Path = DEFAULT_PACKAGE_ROOT,
    strip_markers: bool = True,
) -> Dict[str, List[str]]:
    """``[project.optional-dependencies]``, by default with markers stripped.

    Markers are dropped so that a marked requirement such as
    ``openinference-instrumentation-beeai ; python_version >= '3.11'`` compares
    equal to the bare distribution name declared in ``arthur.py``.  Pass
    ``strip_markers=False`` to compare the markers themselves — an individual
    extra and the ``all`` extra must carry the same ones.
    """
    pyproject = tomllib.loads((package_root / PYPROJECT).read_text())
    optional = pyproject["project"]["optional-dependencies"]
    if not strip_markers:
        return {extra: list(requirements) for extra, requirements in optional.items()}
    return {
        extra: [requirement.split(";")[0].strip() for requirement in requirements]
        for extra, requirements in optional.items()
    }


def marker_of(requirement: str) -> str:
    """The environment marker on a requirement string, or "" if unmarked."""
    _, _, marker = requirement.partition(";")
    return marker.strip()


def load_documented(
    package_root: pathlib.Path = DEFAULT_PACKAGE_ROOT,
) -> Dict[str, str]:
    """README "Supported instrumentors" table as ``{extra: method_name}``."""
    return dict(README_ROW.findall((package_root / README).read_text()))


def _load_from_ref(
    package_root: pathlib.Path,
    ref: str,
) -> Optional[Dict[str, Instrumentor]]:
    """Load the registry as it stood at a git ref, or None if unavailable."""
    toplevel = subprocess.run(
        ["git", "-C", str(package_root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if toplevel.returncode != 0:
        return None
    prefix = package_root.relative_to(pathlib.Path(toplevel.stdout.strip()))

    # Only arthur.py is fetched: the declarations live there and nowhere else.
    # Requiring pyproject.toml and README.md to exist at the ref too would make
    # the fallback fire whenever either file moved — which is exactly what
    # happened when README.md moved into python/.
    blob = subprocess.run(
        ["git", "-C", str(package_root), "show", f"{ref}:{prefix / ARTHUR_SOURCE}"],
        capture_output=True,
        text=True,
    )
    if blob.returncode != 0:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        checkout = pathlib.Path(tmp)
        destination = checkout / ARTHUR_SOURCE
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(blob.stdout)
        try:
            return load_instrumentors(checkout)
        except (RegistryError, SyntaxError):
            return None


def changed_since(
    ref: str,
    package_root: pathlib.Path = DEFAULT_PACKAGE_ROOT,
) -> List[Instrumentor]:
    """Declarations that are new or altered relative to ``ref``.

    Returns every declaration when the ref cannot be read (shallow clone, first
    commit, unparseable history) — verifying too much is the safe direction.
    """
    current = load_instrumentors(package_root)
    baseline = _load_from_ref(package_root, ref)
    if baseline is None:
        return sorted(current.values())
    return sorted(
        instrumentor
        for method, instrumentor in current.items()
        if baseline.get(method) != instrumentor
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=DEFAULT_PACKAGE_ROOT,
        help="package root containing pyproject.toml (default: the SDK's python/)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON for a CI matrix")
    parser.add_argument(
        "--changed-since",
        metavar="REF",
        help="restrict output to declarations new or altered since this git ref",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if args.changed_since:
        instrumentors = changed_since(args.changed_since, root)
    else:
        instrumentors = sorted(load_instrumentors(root).values())

    if args.json:
        json.dump(
            [instrumentor._asdict() for instrumentor in instrumentors],
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0

    if not instrumentors:
        print("No instrumentor declarations selected.")
        return 0
    width = max(len(instrumentor.method) for instrumentor in instrumentors)
    for instrumentor in instrumentors:
        print(
            f"{instrumentor.method:<{width}}  "
            f"[{instrumentor.extra}]  {instrumentor.module_path}.{instrumentor.class_name}",
        )
    print(f"\n{len(instrumentors)} declaration(s), {len(UNSUPPORTED)} excluded.")
    for extra, reason in sorted(UNSUPPORTED.items()):
        print(f"  excluded: {extra} — {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
