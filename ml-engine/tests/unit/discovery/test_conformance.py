"""ai-detection-spec's conformance vectors, run through this engine's matcher.

SPEC.md 9: a matcher conforms when it meets section 6 and gives the expected result for
every vector. Upstream holds `bin/classify` to them. These hold what this engine wraps
around it -- reading a catalog document, refusing what the spec refuses, and the findings
it builds -- to the same expectations, from the vectors vendored at the same ref.
"""

import json
import pathlib
import re
from typing import Any

import pytest

from discovery.catalog import Matcher

VECTORS = json.loads(
    (
        pathlib.Path(__file__).resolve().parents[3]
        / "src"
        / "ml_engine"
        / "discovery"
        / "_vendor"
        / "vectors.json"
    ).read_text(),
)["vectors"]

# A member a matcher must ignore (SPEC.md 5.1), carrying each row's index through the result.
ROW = "conformance_row"


def _finding(f: dict[str, Any]) -> dict[str, Any]:
    """A vector's finding with the members it leaves out at their defaults (SPEC.md 6.6)."""
    return {
        "evidence": f["evidence"],
        "running": f.get("running", False),
        "superseded": f.get("superseded", []),
        "only_superseded": f.get("only_superseded", False),
    }


@pytest.mark.parametrize("vector", VECTORS, ids=[v["id"] for v in VECTORS])
def test_the_matcher_gives_each_vectors_result(vector: dict[str, Any]) -> None:
    expect = vector["expect"]
    catalog = json.dumps(vector["catalog"])
    if "error" in expect:
        # A refusal names what it refused.
        with pytest.raises(ValueError, match=re.escape(expect["error"])):
            Matcher.from_source(catalog_json=catalog)
        return

    rows = [{**r, ROW: str(i)} for i, r in enumerate(vector["rows"])]
    result = Matcher.from_source(catalog_json=catalog).match(rows)

    matches: list[Any] = [None] * len(rows)
    findings = {}
    for f in result.findings:
        evidence = [int(r[ROW]) for r in f.evidence]
        for i in evidence:
            matches[i] = f.agent_id
        findings[f.agent_id] = {
            "evidence": evidence,
            "running": f.running,
            "superseded": list(f.superseded),
            "only_superseded": f.only_superseded,
        }
    assert matches == expect["matches"]
    assert findings == {a: _finding(f) for a, f in expect["findings"].items()}

    # The result counts unmatched and dropped rows rather than listing them, so the rows
    # that are neither matched nor scan markers are held to the two lists together.
    assert result.unmatched == len(expect["unmatched"])
    assert result.dropped == len(expect["dropped"])
    neither = [
        i for i, r in enumerate(rows) if matches[i] is None and r["kind"] != "scan"
    ]
    assert neither == sorted(expect["unmatched"] + expect["dropped"])

    for group in ("scans", "absences", "gaps"):
        if group in expect:
            assert sorted(int(r[ROW]) for r in getattr(result, group)) == expect[group]
