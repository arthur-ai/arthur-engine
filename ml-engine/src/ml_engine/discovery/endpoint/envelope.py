"""Reading the `arthur1.` value an MDM hands back for one device.

Arthur's wire format, not osquery's and not any MDM's: the endpoint writes

    printf 'arthur1.'; gzip -9 -c inventory.json | base64 | tr -d '
'

and this reverses it. The payload is a BARE JSON ARRAY of ai-detection-spec evidence rows
(SPEC.md 5) -- serial, host and OS are deliberately absent, because the MDM already knows them.

Returns a named outcome rather than rows or an exception. An unreadable value and a Mac
with no agents on it are different facts, and returning `[]` for a truncated payload would
report a well-equipped Mac as clean. It never raises on input either: one corrupt value
must not fail the scan for the other nine thousand devices.
"""

import base64
import binascii
import gzip
import io
import json
import pathlib
import re
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# Eight bytes. The dot is part of it: a future `arthur2.` is a different prefix rather
# than a version field inside the payload.
FRAME_PREFIX = "arthur1."

# Written INSTEAD of the payload when it would exceed the 256 KiB cap, unframed so an MDM
# can match it without decoding. The tail is the size the framed value would have been.
OVERSIZE_PREFIX = "ERROR:oversize:"

# The attribute script's fallback when it cannot read the file. A deployment fault, not a
# fact about the Mac.
NO_CACHE = "no-cache"

# THE ROW CONTRACT IS THE SPEC'S, read off its vendored evidence schema rather than restated
# here. Validating with jsonschema itself costs ~25 ms for a 1,000-row device, against ~0.6 ms
# to match one, so the schema's rules are applied by _row_problem() and a test holds that to
# jsonschema's verdict.
_EVIDENCE = json.loads(
    (
        pathlib.Path(__file__).resolve().parent.parent
        / "_vendor"
        / "evidence.schema.json"
    ).read_text(),
)
_ROW = _EVIDENCE["$defs"]["row"]
# The members the spec names. One a row omits reads as the empty string (SPEC.md 5.1).
_MEMBERS = tuple(_ROW["properties"])
_REQUIRED = tuple(_ROW["required"])
_KIND = re.compile(_ROW["properties"]["kind"]["pattern"])
_SCAN_KIND = _ROW["if"]["properties"]["kind"]["const"]
_SCAN_REQUIRED = tuple(_ROW["then"]["required"])
_SCAN_VER = re.compile(_ROW["then"]["properties"]["ver"]["pattern"])
_OUTCOMES = _EVIDENCE["$defs"]["scan_outcome"]["anyOf"]
_OUTCOME_WORDS = frozenset(w for o in _OUTCOMES for w in o.get("enum", ()))
_OUTCOME_PATTERNS = tuple(re.compile(o["pattern"]) for o in _OUTCOMES if "pattern" in o)

# Three orders of magnitude above the measured ~127 KB payload. Decompressing untrusted
# bytes without a limit is how a scan job becomes an out-of-memory kill. RecursionError is
# caught alongside the parse errors for the same reason: deeply nested arrays are cheap to
# write and would otherwise escape.
MAX_DECOMPRESSED_BYTES = 16 * 1024 * 1024


class EnvelopeOutcome(str, Enum):
    """What a device's attribute value turned out to be.

    The three failure members are not interchangeable: `NEVER_REPORTED` is a Mac the MDM
    has not heard from, `NO_CACHE` a Mac that reported while the collector never ran, and
    `MALFORMED` bytes we cannot read -- the only one indicating a defect on this side.
    """

    OK = "ok"
    """The value decoded. `rows` holds the payload."""

    OVERSIZE = "oversize"
    """The scan ran and its payload would not fit. `detail` is the would-be byte count."""

    NO_CACHE = "no-cache"
    """The attribute script could not read the file. Nothing has been written."""

    NEVER_REPORTED = "never-reported"
    """Blank. The MDM has not had inventory from this Mac since the attribute was made."""

    MALFORMED = "malformed"
    """Bytes arrived and could not be read. `detail` says where it broke."""


@dataclass(frozen=True)
class Envelope:
    """One device's attribute value, decoded or explained.

    `rows` is populated only for `OK`, so an empty `rows` never means "this Mac is clean"
    unless `outcome is OK`. Forcing that distinction is what the type is for.

    `ignored` names the members the rows carried and the spec does not, which were left out
    of `rows` unread.
    """

    outcome: EnvelopeOutcome
    rows: tuple[dict[str, Any], ...] = field(default=())
    detail: Optional[str] = None
    ignored: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return self.outcome is EnvelopeOutcome.OK

    @property
    def oversize_bytes(self) -> Optional[int]:
        """The size the framed value would have been, for `OVERSIZE` only."""
        if self.outcome is not EnvelopeOutcome.OVERSIZE or self.detail is None:
            return None
        try:
            return int(self.detail)
        except ValueError:
            return None


def _malformed(reason: str) -> Envelope:
    return Envelope(outcome=EnvelopeOutcome.MALFORMED, detail=reason)


def _gunzip_bounded(blob: bytes) -> bytes:
    """Decompress one gzip member, refusing anything past the bound.

    Reads one byte past the limit so an overrun is detected rather than silently
    truncated: a cut landing on a row boundary would parse as valid JSON.
    """
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
        out = gz.read(MAX_DECOMPRESSED_BYTES + 1)
    if len(out) > MAX_DECOMPRESSED_BYTES:
        raise ValueError(
            f"payload expands past the {MAX_DECOMPRESSED_BYTES}-byte bound",
        )
    return out


def _row_problem(row: Any) -> Optional[str]:
    """Why `row` is not an evidence row the spec's schema admits, or None.

    Values from the payload are quoted short: the value is of unknown provenance here.
    """
    if not isinstance(row, dict):
        return f"is {type(row).__name__}, expected an object"
    missing = [m for m in _REQUIRED if m not in row]
    if missing:
        return f"is missing {missing}"
    # Every member is a string, those the spec names and any a binding adds. A non-string
    # reaches the matcher as-is -- a null `id` raises TypeError inside its regex and takes the
    # whole scan with it.
    bad = sorted(k for k, v in row.items() if not isinstance(v, str))
    if bad:
        return f"has non-string member(s): {bad}"
    if not _KIND.search(row["kind"]):
        return f"has kind {row['kind'][:40]!r}, which is not a kind name"
    if row["kind"] == _SCAN_KIND:
        missing = [m for m in _SCAN_REQUIRED if m not in row]
        if missing:
            return f"is a scan marker missing {missing}"
        if not _SCAN_VER.search(row["ver"]):
            return f"is a scan marker whose ver {row['ver'][:40]!r} is not unix seconds"
        outcome = row["extra"]
        if outcome not in _OUTCOME_WORDS and not any(
            p.search(outcome) for p in _OUTCOME_PATTERNS
        ):
            return (
                f"is a scan marker with an outcome outside the spec's: {outcome[:40]!r}"
            )
    return None


def _validate_rows(
    doc: Any,
) -> tuple[Optional[tuple[dict[str, Any], ...]], Optional[str], tuple[str, ...]]:
    """Check the decoded document against the spec's evidence schema (SPEC.md 5).

    One wrong row fails the whole device rather than being dropped: a row the schema refuses
    means this reader may be misreading all of them, and keeping the rest would turn a format
    change into a slow leak of records. A member a row omits reads as the empty string.

    A MEMBER THE SPEC DOES NOT NAME IS IGNORED, AND THAT MEANS NOT CARRIED. A binding may add
    one, a string like every member, and a matcher must ignore it; this reader is also the
    privacy boundary, so it keeps only the members the spec names. A collector that starts
    writing what it read -- a prompt, a file -- has that value go no further than here, and
    the member is named, never its value. Returns (rows, reason, the names ignored).
    """
    if not isinstance(doc, list):
        return None, f"payload is {type(doc).__name__}, expected a JSON array", ()

    rows: list[dict[str, Any]] = []
    ignored: set[str] = set()
    for i, row in enumerate(doc):
        problem = _row_problem(row)
        if problem is not None:
            return None, f"row {i} {problem} (SPEC.md 5)", ()
        ignored.update(k for k in row if k not in _MEMBERS)
        rows.append({m: row.get(m, "") for m in _MEMBERS})

    return tuple(rows), None, tuple(sorted(name[:40] for name in ignored))


def read(value: Optional[str]) -> Envelope:
    """Decode one device's inventory attribute value.

    Accepts `None` and the empty string, because MDMs return both for a device whose
    attribute has never been populated, and neither is an error.
    """
    if value is None:
        return Envelope(outcome=EnvelopeOutcome.NEVER_REPORTED)

    # The file ends in a newline; the attribute script's command substitution strips it
    # before the MDM sees it. Belt-and-braces for a value read by some other route.
    text = value.strip()

    if not text:
        return Envelope(outcome=EnvelopeOutcome.NEVER_REPORTED)

    if text == NO_CACHE:
        return Envelope(outcome=EnvelopeOutcome.NO_CACHE)

    if text.startswith(OVERSIZE_PREFIX):
        return Envelope(
            outcome=EnvelopeOutcome.OVERSIZE,
            detail=text[len(OVERSIZE_PREFIX) :],
        )

    if not text.startswith(FRAME_PREFIX):
        # Does not echo the value: up to 256 KiB, and of unknown provenance here.
        return _malformed(f"value does not start with {FRAME_PREFIX!r}")

    encoded = text[len(FRAME_PREFIX) :]
    if not encoded:
        return _malformed("framed value carries no payload")

    try:
        blob = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        return _malformed(f"base64 did not decode: {exc}")

    try:
        raw = _gunzip_bounded(blob)
    except (OSError, EOFError, ValueError, zlib.error) as exc:
        # zlib.error needs naming separately: it derives from Exception, not OSError or
        # ValueError. gzip covers a bad header (BadGzipFile) and truncation (EOFError);
        # a GOOD header with a corrupted body raises zlib.error and would escape.
        return _malformed(f"gzip did not decompress: {exc}")

    return read_document(raw)


def read_document(raw: bytes) -> Envelope:
    """Decode the payload itself: the JSON array the frame wraps.

    What `read` does once the frame is off, and what a reader with the runner's file in
    hand does instead -- no carrier sat between them, so there is no frame to remove, but
    the rows owe the same contract. Bounded like the frame's contents, since the file
    is as large as whatever the runner wrote.
    """
    if len(raw) > MAX_DECOMPRESSED_BYTES:
        return _malformed(
            f"payload is past the {MAX_DECOMPRESSED_BYTES}-byte bound",
        )

    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        return _malformed(f"payload is not valid JSON: {exc}")

    rows, reason, ignored = _validate_rows(doc)
    if reason is not None:
        return _malformed(reason)

    assert rows is not None
    return Envelope(outcome=EnvelopeOutcome.OK, rows=rows, ignored=ignored)
