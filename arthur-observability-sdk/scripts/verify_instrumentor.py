#!/usr/bin/env python3
"""Verifies one ``instrument_*`` declaration against the installed package.

``tests/test_instrumentors.py`` checks that the four registry locations agree on
*names*.  Nothing in it reads ``module_path`` or ``class_name``, which are the
only two arguments that decide whether ``arthur.instrument_x()`` works — they
appear nowhere but the call that consumes them.  This script closes that gap.

Two tiers, because the openinference packages differ in what they need:

  Tier 1 (always runs) — the declared ``class_name`` is actually exported by the
    installed ``module_path``, checked by parsing the installed package's source
    rather than importing it.  This needs only the extra, never the instrumented
    framework, so it runs for every declaration.  It is what catches a wrong
    class name, or a package that ships a SpanProcessor instead of an
    instrumentor.

  Tier 2 (runs when the module imports) — the real code path end to end:
    ``importlib.import_module`` -> ``getattr`` -> ``cls()`` ->
    ``.instrument(tracer_provider=...)`` -> ``.uninstrument()``.
    Several packages import the instrumented framework at module scope
    (``bedrock`` needs ``botocore``, ``baml`` needs ``baml_py``, ...), which is
    not installed here.  That is reported as a skip, not a failure — tier 1 has
    already checked the declaration itself.

Usage, in an environment where the SDK and the relevant extra are installed:

    pip install "arthur_observability_sdk-*.whl[openai]"
    python3 scripts/verify_instrumentor.py --method instrument_openai

Exit status is 0 when the outcome matches expectation and 1 when it does not.
``KNOWN_BROKEN`` declarations are held to the opposite expectation: they must
still fail, so fixing one forces its entry to be removed instead of rotting.

Note that a tier-2 failure with a missing *framework* module surfaces from the
SDK as "Missing optional dependency '<the extra's package>' ... pip install
arthur-observability-sdk[extra]" even though that package is installed —
``Arthur._instrument`` catches every ImportError in the chain and rewrites it.
This script reports the underlying cause instead.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import pathlib
import sys
import traceback
from typing import List, Optional, Tuple

from instrumentor_registry import Instrumentor, load_instrumentors

# Tier 1 verifies the declaration; anything outside this namespace that fails to
# import is the instrumented framework, which this script does not install.
OWN_NAMESPACE = "openinference"


def _exported_names(source: str) -> Tuple[List[str], bool]:
    """Names reachable via ``getattr`` on a module, plus whether it has a hook.

    A module-level ``__getattr__`` (the ``codex`` package uses one) can serve
    names that no static scan will see, so its presence makes a negative result
    inconclusive and defers the verdict to tier 2.
    """
    tree = ast.parse(source)
    names: List[str] = []
    has_getattr_hook = False

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            names.append(node.name)
            if node.name == "__getattr__":
                has_getattr_hook = True
        elif isinstance(node, ast.ImportFrom):
            names.extend(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.extend(
                (alias.asname or alias.name).split(".")[0] for alias in node.names
            )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
                    # __all__ is the package's own statement of what it exports.
                    if target.id == "__all__" and isinstance(
                        node.value,
                        (ast.List, ast.Tuple),
                    ):
                        names.extend(
                            element.value
                            for element in node.value.elts
                            if isinstance(element, ast.Constant)
                            and isinstance(element.value, str)
                        )
    return names, has_getattr_hook


def check_declaration(instrumentor: Instrumentor) -> Tuple[bool, str]:
    """Tier 1: does the installed module export the declared class name?"""
    try:
        spec = importlib.util.find_spec(instrumentor.module_path)
    except (ImportError, ValueError) as error:
        return False, f"cannot locate module '{instrumentor.module_path}': {error}"
    if spec is None or spec.origin is None:
        return False, f"module '{instrumentor.module_path}' is not installed"

    source = pathlib.Path(spec.origin).read_text()
    try:
        names, has_getattr_hook = _exported_names(source)
    except SyntaxError as error:
        return False, f"cannot parse {spec.origin}: {error}"

    if instrumentor.class_name in names:
        return (
            True,
            f"'{instrumentor.class_name}' exported by {instrumentor.module_path}",
        )
    if has_getattr_hook:
        return True, (
            f"'{instrumentor.class_name}' not found statically, but "
            f"{instrumentor.module_path} defines __getattr__ — deferring to tier 2"
        )

    candidates = sorted(name for name in names if "Instrumentor" in name)
    hint = (
        f" Module exports: {candidates}."
        if candidates
        else " Module exports no *Instrumentor."
    )
    return False, (
        f"'{instrumentor.class_name}' is not exported by "
        f"'{instrumentor.module_path}'.{hint}"
    )


def _tracer_provider() -> object:
    """A real in-process provider, so the ``tracer_provider=`` kwarg is exercised."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    return provider


def _missing_framework_module(instrumentor: Instrumentor) -> Optional[str]:
    """The framework module the package needs but that is not installed.

    Imports ``module_path`` directly so the real exception is visible rather than
    the one ``Arthur._instrument`` rewrites it into.  Returns None when the
    module imports, or when the missing module is the declaration's own.
    """
    try:
        importlib.import_module(instrumentor.module_path)
    except ModuleNotFoundError as error:
        missing = error.name or ""
        if missing.split(".")[0] == OWN_NAMESPACE:
            return None  # the declared package itself is absent — a real failure
        return missing
    except BaseException:
        # Anything else — including a package that raises NameError on import,
        # as monkai-agent 0.0.1 does — is a real failure for the user calling
        # instrument_*().  Return None so tier 2 runs and records it properly
        # instead of letting the exception abort a --all sweep.
        return None
    return None


def exercise(instrumentor: Instrumentor) -> Tuple[Optional[bool], str]:
    """Tier 2: call the method through a real ``Arthur``.

    Returns (None, reason) when the framework is absent and the check cannot run.
    """
    missing = _missing_framework_module(instrumentor)
    if missing:
        return (
            None,
            f"needs the instrumented framework ('{missing}'), not installed here",
        )

    from arthur_observability_sdk import Arthur

    arthur = Arthur(service_name="instrumentor-verification", enable_telemetry=False)
    # enable_telemetry=False leaves _tracer_provider unset, which would skip the
    # tracer_provider kwarg entirely.  Inject one the way the unit tests do
    # (see arthur-observability-sdk/CLAUDE.md) so the full call shape is covered.
    arthur._tracer_provider = _tracer_provider()

    method = getattr(arthur, instrumentor.method, None)
    if method is None:
        return False, f"Arthur has no attribute '{instrumentor.method}'"

    try:
        handle = method()
    except Exception:
        return False, traceback.format_exc()

    if handle is None:
        return False, f"{instrumentor.method}() returned None"

    detail = f"instantiated {type(handle).__module__}.{type(handle).__name__}"
    if getattr(handle, "is_instrumented_by_opentelemetry", None) is False:
        detail += "; patching skipped (framework not installed)"

    uninstrument = getattr(handle, "uninstrument", None)
    if callable(uninstrument):
        try:
            uninstrument()
        except Exception:
            return False, (
                "instrument() succeeded but uninstrument() raised:\n"
                + traceback.format_exc()
            )
    return True, detail


def verify(instrumentor: Instrumentor) -> int:
    """Run both tiers and compare the outcome to what ``KNOWN_BROKEN`` expects."""
    label = f"{instrumentor.method}() -> {instrumentor.module_path}.{instrumentor.class_name}"
    expected_broken = instrumentor.known_broken

    declared_ok, declared_detail = check_declaration(instrumentor)
    lines = [f"      tier 1: {declared_detail}"]

    if declared_ok:
        exercised, exercise_detail = exercise(instrumentor)
        if exercised is None:
            lines.append(f"      tier 2: skipped — {exercise_detail}")
        else:
            lines.append(f"      tier 2: {exercise_detail}")
        worked = exercised is not False
    else:
        worked = False

    body = "\n".join(lines)

    if worked and not expected_broken:
        print(f"PASS  {label}\n{body}")
        return 0

    if worked and expected_broken:
        print(
            f"FAIL  {label}\n{body}\n"
            f"      This declaration is listed in KNOWN_BROKEN but now works.\n"
            f"      Remove it from KNOWN_BROKEN in scripts/instrumentor_registry.py.\n"
            f"      Recorded reason: {expected_broken}",
        )
        return 1

    if expected_broken:
        print(f"XFAIL {label}\n{body}\n      Broken as recorded: {expected_broken}")
        return 0

    print(
        f"FAIL  {label}\n{body}\n"
        f"      pip install arthur-observability-sdk[{instrumentor.extra}] then "
        f"{instrumentor.method}() does not work.\n"
        f"      Check module_path and class_name against the published package.",
    )
    return 1


def verify_all() -> int:
    """Verify every declaration in one process — for an ``[all]`` extra install."""
    instrumentors = sorted(load_instrumentors().values())
    failed = []
    for instrumentor in instrumentors:
        if verify(instrumentor) != 0:
            failed.append(instrumentor.method)
        print()

    print(f"{len(instrumentors) - len(failed)}/{len(instrumentors)} as expected.")
    if failed:
        print(f"Unexpected results: {', '.join(failed)}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--method", help="e.g. instrument_openai")
    selector.add_argument("--extra", help="e.g. openai")
    selector.add_argument(
        "--all",
        action="store_true",
        help="verify every declaration in one process (needs the 'all' extra installed)",
    )
    args = parser.parse_args()

    if args.all:
        return verify_all()

    instrumentors = load_instrumentors()
    if args.method:
        instrumentor = instrumentors.get(args.method)
        if instrumentor is None:
            parser.error(f"no such method: {args.method}")
    else:
        instrumentor = next(
            (item for item in instrumentors.values() if item.extra == args.extra),
            None,
        )
        if instrumentor is None:
            parser.error(f"no instrument_* method declares extra: {args.extra}")

    return verify(instrumentor)


if __name__ == "__main__":
    sys.exit(main())
