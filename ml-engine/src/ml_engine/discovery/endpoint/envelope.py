"""Reading the `arthur1.` value an MDM hands back for one device.

Arthur's wire format, not osquery's and not any MDM's: the endpoint writes

    printf 'arthur1.'; gzip -9 -c inventory.json | base64 | tr -d '
'

and this reverses it. The payload is a BARE JSON ARRAY of six-column rows -- serial, host
and OS are deliberately absent, because the MDM already knows them.

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

# The six-column contract. Order carries it upstream; by the time it is JSON, the keys do.
ROW_COLUMNS = frozenset({"kind", "id", "ver", "loc", "extra", "perms"})

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


def _validate_rows(
    doc: Any,
) -> tuple[Optional[tuple[dict[str, Any], ...]], Optional[str]]:
    """Check the decoded document against the six-column contract.

    One wrong row fails the whole device rather than being dropped: the columns are the
    wire format, so a row that does not match means this reader may be misreading all of
    them, and keeping the rest would turn a format change into a slow leak of findings.
    """
    if not isinstance(doc, list):
        return None, f"payload is {type(doc).__name__}, expected a JSON array"

    for i, row in enumerate(doc):
        if not isinstance(row, dict):
            return None, f"row {i} is {type(row).__name__}, expected an object"
        bad = [k for k, v in row.items() if not isinstance(v, str)]
        if bad and frozenset(row) == ROW_COLUMNS:
            # Every column is a JSON string in the six-column contract. A non-string
            # reaches the matcher as-is -- a null `id` raises TypeError inside its regex
            # and takes the whole scan with it.
            return None, f"row {i} has non-string column(s): {sorted(bad)}"

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
    """Decode one device's `AI Inventory` attribute value.

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

    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        return _malformed(f"payload is not valid JSON: {exc}")

    rows, reason = _validate_rows(doc)
    if reason is not None:
        return _malformed(reason)

    assert rows is not None
    return Envelope(outcome=EnvelopeOutcome.OK, rows=rows)
