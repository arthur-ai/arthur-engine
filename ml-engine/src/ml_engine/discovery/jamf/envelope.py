"""Reading the `arthur1.` Extension Attribute value Jamf hands back.

This is the one piece of the endpoint connector that is purely Arthur's wire format:
the endpoint writes the value, this reads it, and osquery has no opinion about either.
The producing side lives in `arthur-discovery/tools/build-collector.py`, which frames
the value as::

    printf 'arthur1.'; gzip -9 -c inventory.json | base64 | tr -d '\n'

so the inverse is prefix, base64, gunzip, parse -- and nothing else. There is no
envelope object to unwrap: the payload is a BARE JSON ARRAY of six-column rows. The
`{"scan": ..., "findings": ...}` shape in that repo's `docs/architecture.md` describes
what the collector holds AFTER joining Jamf's own computer record, not what is on the
wire; `serial`, `host` and `os` are deliberately absent from the value because Jamf
already knows them and a second source of truth for a Mac's identity is a liability.

WHY THIS RETURNS AN OUTCOME RATHER THAN RAISING OR RETURNING ROWS.
An unreadable value and a Mac with no agents on it are different facts, and the entire
endpoint design exists to keep them apart -- every silent defect this project has
shipped was a wrong answer that looked like a right one. A reader that returned `[]`
for a truncated payload would report a well-equipped Mac as clean, which is the one
error the producing side goes to considerable lengths to avoid. So every failure here
is named, and the caller is handed something it has to branch on.

It also never raises on input. One Mac with a corrupt value must not fail the scan for
the other nine thousand -- that device is reported as unread and the run continues.
"""

import base64
import binascii
import gzip
import io
import json
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# The frame, exactly as the producing side writes it. Eight bytes, and the dot is part
# of it -- `arthur1.` is the version, so a future `arthur2.` is a different prefix
# rather than a field inside the payload.
FRAME_PREFIX = "arthur1."

# Written INSTEAD of the payload when the framed value would exceed the collector's
# 256 KiB cap, and deliberately unframed so a Jamf Smart Group can match it without
# decoding anything. The integer tail is the size the framed value WOULD have been.
OVERSIZE_PREFIX = "ERROR:oversize:"

# The Extension Attribute script's own fallback, emitted when it cannot read the file
# the scheduled job should have written. A deployment fault, not a fact about the Mac.
NO_CACHE = "no-cache"

# The six-column contract, enforced on every row. Order is the contract upstream, but
# by the time it is JSON the keys carry it, so a set is the right check here.
ROW_COLUMNS = frozenset({"kind", "id", "ver", "loc", "extra", "perms"})

# A bound on what the gzip member may expand to. The measured payload is ~127 KB and
# the framed value is capped at 256 KiB, so this is three orders of magnitude of slack
# -- it exists because decompressing attacker-shaped bytes without a limit is how a
# scan job becomes an out-of-memory kill, not because any real Mac approaches it.
MAX_DECOMPRESSED_BYTES = 16 * 1024 * 1024


class EnvelopeOutcome(str, Enum):
    """What a single device's attribute value turned out to be.

    Closed, and every member is a distinct thing a consumer may need to act on. The
    three failure members are NOT interchangeable: `NEVER_REPORTED` is a Mac Jamf has
    not heard from, `NO_CACHE` is a Mac that reported while the collector was not
    installed or never ran, and `MALFORMED` means we hold bytes we cannot read, which
    is the only one that indicates a defect on this side.
    """

    OK = "ok"
    """The value decoded. `rows` holds the payload."""

    OVERSIZE = "oversize"
    """The scan ran and its payload would not fit. `detail` is the would-be byte count."""

    NO_CACHE = "no-cache"
    """The Extension Attribute could not read the file. Nothing has been written."""

    NEVER_REPORTED = "never-reported"
    """Blank. This Mac has not submitted inventory since the attribute was created."""

    MALFORMED = "malformed"
    """Bytes arrived and could not be read. `detail` says where it broke."""


@dataclass(frozen=True)
class Envelope:
    """One device's attribute value, decoded or explained.

    `rows` is populated only for `OK` and is empty for every other outcome -- an empty
    `rows` therefore never means "this Mac is clean" unless `outcome is OK`, which is
    the distinction the whole type exists to force.
    """

    outcome: EnvelopeOutcome
    rows: tuple[dict[str, Any], ...] = field(default=())
    detail: Optional[str] = None

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

    Reads one byte more than the limit so an overrun is detected rather than silently
    truncated -- a truncated payload would parse as valid JSON if the cut happened to
    land on a boundary, which is exactly the plausible-but-wrong failure this module is
    written against.
    """
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
        out = gz.read(MAX_DECOMPRESSED_BYTES + 1)
    if len(out) > MAX_DECOMPRESSED_BYTES:
        raise ValueError(
            f"payload expands past the {MAX_DECOMPRESSED_BYTES}-byte bound",
        )
    return out


def _validate_rows(
    doc: Any,
) -> tuple[Optional[tuple[dict[str, Any], ...]], Optional[str]]:
    """Check the decoded document against the six-column contract.

    Returns `(rows, None)` or `(None, reason)`. A row whose key set differs is treated
    as a contract violation for the whole device rather than dropped: the columns are
    the wire format, so one wrong row means this reader may be misreading every other
    row too, and quietly keeping the rest would turn a format change into a slow leak
    of missing findings.
    """
    if not isinstance(doc, list):
        return None, f"payload is {type(doc).__name__}, expected a JSON array"

    for i, row in enumerate(doc):
        if not isinstance(row, dict):
            return None, f"row {i} is {type(row).__name__}, expected an object"
        keys = frozenset(row)
        if keys != ROW_COLUMNS:
            missing = sorted(ROW_COLUMNS - keys)
            extra = sorted(keys - ROW_COLUMNS)
            detail = ", ".join(
                part
                for part in (
                    f"missing {missing}" if missing else "",
                    f"unexpected {extra}" if extra else "",
                )
                if part
            )
            return None, f"row {i} breaks the six-column contract: {detail}"

    return tuple(doc), None


def read(value: Optional[str]) -> Envelope:
    """Decode one `AI Inventory` Extension Attribute value.

    Accepts `None` and the empty string, because Jamf returns both for a computer whose
    attribute has never been populated, and neither is an error.
    """
    if value is None:
        return Envelope(outcome=EnvelopeOutcome.NEVER_REPORTED)

    # The file on disk ends in a newline. Command substitution in the Extension
    # Attribute script strips it before Jamf ever sees it, so this is belt-and-braces
    # against a value read by some other route.
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
        # Deliberately does not echo the value: it is up to 256 KiB and, on the paths
        # that reach here, of unknown provenance.
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
        # zlib.error is listed explicitly because it derives from Exception and from
        # neither OSError nor ValueError. gzip raises BadGzipFile (an OSError) for a bad
        # header and EOFError for a truncated member, but a member with a GOOD header and
        # a corrupted deflate body raises zlib.error -- which would escape this function,
        # break the never-raises contract above, and fail a whole fleet scan for one
        # device's bad value.
        return _malformed(f"gzip did not decompress: {exc}")

    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _malformed(f"payload is not valid JSON: {exc}")

    rows, reason = _validate_rows(doc)
    if reason is not None:
        return _malformed(reason)

    assert rows is not None
    return Envelope(outcome=EnvelopeOutcome.OK, rows=rows)
