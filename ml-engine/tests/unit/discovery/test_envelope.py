"""The `arthur1.` reader, against real collector output and every failure it can name.

The round-trip test at the bottom runs against `/var/lib/arthur/inventory.ea` when this
machine has actually run the deployable, and skips otherwise. It is the only test here
that proves the reader against bytes nobody in this repo wrote, which is the whole
point of it -- the synthetic fixtures below all encode MY understanding of the frame,
so they would agree with a reader that was wrong in the same way.
"""

import base64
import gzip
import io
import json
import pathlib

import pytest

from discovery.endpoint.envelope import (
    FRAME_PREFIX,
    MAX_DECOMPRESSED_BYTES,
    EnvelopeOutcome,
    read,
)

COLLECTOR_OUTPUT = pathlib.Path("/var/lib/arthur")


def row(
    kind: str = "app",
    id: str = "com.example.thing",
    **over: str,
) -> dict[str, str]:
    """A six-column row. Every column present, because that is the contract."""
    base = {
        "kind": kind,
        "id": id,
        "ver": "1.0",
        "loc": "/Applications/T.app",
        "extra": "",
        "perms": "",
    }
    base.update(over)
    return base


def frame(doc: object) -> str:
    """Build a framed value the way `build-collector.py` does.

    `printf 'arthur1.'; gzip -9 -c | base64 | tr -d '\\n'` -- kept as one expression so
    a change to the producing side has one place to be mirrored.
    """
    raw = json.dumps(doc).encode()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(raw)
    return FRAME_PREFIX + base64.b64encode(buf.getvalue()).decode()


# --- the outcomes that are not failures -------------------------------------------


def test_framed_payload_decodes_to_its_rows() -> None:
    env = read(frame([row(), row(kind="npm", id="@anthropic-ai/claude-code")]))
    assert env.outcome is EnvelopeOutcome.OK
    assert env.ok
    assert len(env.rows) == 2
    assert env.rows[1]["id"] == "@anthropic-ai/claude-code"


def test_an_empty_array_is_a_valid_payload_not_a_failure() -> None:
    """A Mac that ran the scan and matched nothing still produced a real reading.

    It is only distinguishable from a Mac that could not be read because the outcome
    says so -- which is why `rows` alone is never the answer to "is this Mac clean".
    """
    env = read(frame([]))
    assert env.outcome is EnvelopeOutcome.OK
    assert env.rows == ()


def test_trailing_newline_is_tolerated() -> None:
    assert read(frame([row()]) + "\n").outcome is EnvelopeOutcome.OK


# --- the outcomes that are failures, each named separately -------------------------


@pytest.mark.parametrize("value", [None, "", "   ", "\n"])
def test_blank_means_never_reported(value: str | None) -> None:
    assert read(value).outcome is EnvelopeOutcome.NEVER_REPORTED


def test_no_cache_is_its_own_outcome() -> None:
    """Not an empty Mac: the attribute could not read the file the job should have written."""
    assert read("no-cache").outcome is EnvelopeOutcome.NO_CACHE


def test_oversize_carries_the_would_be_byte_count() -> None:
    env = read("ERROR:oversize:271044")
    assert env.outcome is EnvelopeOutcome.OVERSIZE
    assert env.oversize_bytes == 271044
    assert env.rows == ()


def test_oversize_with_an_unparseable_tail_still_reports_oversize() -> None:
    """The outcome is the load-bearing half; the count is diagnostics."""
    env = read("ERROR:oversize:")
    assert env.outcome is EnvelopeOutcome.OVERSIZE
    assert env.oversize_bytes is None


def test_oversize_bytes_is_none_for_every_other_outcome() -> None:
    assert read(frame([row()])).oversize_bytes is None


@pytest.mark.parametrize(
    "value,because",
    [
        ("arthur2.abc", "an unknown frame version"),
        ("just some text", "no frame at all"),
        (FRAME_PREFIX, "a frame with no payload"),
        (FRAME_PREFIX + "not!valid!base64", "undecodable base64"),
        (
            FRAME_PREFIX + base64.b64encode(b"not gzip at all").decode(),
            "bytes that are not gzip",
        ),
    ],
)
def test_unreadable_values_are_malformed_not_empty(value: str, because: str) -> None:
    env = read(value)
    assert env.outcome is EnvelopeOutcome.MALFORMED, because
    assert env.rows == ()
    assert env.detail


def test_gzip_of_non_json_is_malformed() -> None:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(b"{not json")
    env = read(FRAME_PREFIX + base64.b64encode(buf.getvalue()).decode())
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert "not valid JSON" in (env.detail or "")


def test_an_object_payload_is_malformed_because_the_wire_shape_is_an_array() -> None:
    env = read(frame({"scan": {}, "findings": []}))
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert "expected a JSON array" in (env.detail or "")


# --- the six-column contract -------------------------------------------------------


def test_a_row_missing_a_column_fails_the_whole_device() -> None:
    """Not dropped. One wrong row means the wire format moved, so every row is suspect."""
    bad = row()
    del bad["perms"]
    env = read(frame([row(), bad]))
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert "row 1" in (env.detail or "")
    assert "perms" in (env.detail or "")


def test_a_row_with_an_unexpected_column_is_also_a_violation() -> None:
    env = read(frame([row(platform="darwin")]))
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert "platform" in (env.detail or "")


def test_a_non_object_row_is_a_violation() -> None:
    env = read(frame([row(), "just a string"]))
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert "row 1" in (env.detail or "")


# --- resource bound ----------------------------------------------------------------


def test_a_compression_bomb_is_refused_rather_than_expanded() -> None:
    """Untrusted-shaped bytes must not be able to turn a scan job into an OOM kill."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9) as gz:
        gz.write(b"\0" * (MAX_DECOMPRESSED_BYTES + 1024))
    env = read(FRAME_PREFIX + base64.b64encode(buf.getvalue()).decode())
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert "bound" in (env.detail or "")


# --- against what actually ships ---------------------------------------------------


@pytest.mark.skipif(
    not (COLLECTOR_OUTPUT / "inventory.ea").is_file(),
    reason="no collector output on this machine; run arthur-discovery's dist/collect.sh",
)
def test_reader_recovers_real_collector_output_byte_for_byte() -> None:
    """The assertion `arthur-discovery/test/run-collector.sh:110-115` makes with `cmp -s`.

    Byte-identity is a property of the decode chain, not of the parsed rows: the payload
    is pretty-printed, so re-serializing it and comparing would fail for a reader that
    is entirely correct.
    """
    ea = (COLLECTOR_OUTPUT / "inventory.ea").read_text()
    expected = (COLLECTOR_OUTPUT / "inventory.json").read_bytes()

    decoded = gzip.GzipFile(
        fileobj=io.BytesIO(
            base64.b64decode(ea.strip()[len(FRAME_PREFIX) :], validate=True),
        ),
    ).read()
    assert decoded == expected

    env = read(ea)
    assert env.outcome is EnvelopeOutcome.OK
    assert len(env.rows) == len(json.loads(expected))
    assert {r["kind"] for r in env.rows} >= {"app", "scan"}


def test_a_corrupted_deflate_body_is_malformed_rather_than_an_exception() -> None:
    """zlib.error derives from Exception, not OSError or ValueError.

    gzip raises BadGzipFile (an OSError) for a bad header and EOFError for a truncated
    member, so both were already caught. A member with a GOOD header and a corrupted
    body raises zlib.error, which escaped -- breaking the never-raises contract and
    failing an entire fleet scan for one device's bad value.
    """
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(json.dumps([row() for _ in range(40)]).encode())
    raw = bytearray(buf.getvalue())
    for i in range(
        20,
        60,
    ):  # corrupt the deflate stream, leave the 10-byte header intact
        raw[i] ^= 0xFF

    env = read(FRAME_PREFIX + base64.b64encode(bytes(raw)).decode())
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert "gzip did not decompress" in (env.detail or "")


@pytest.mark.parametrize(
    "value,column",
    [(None, "id"), (7, "ver"), ({"a": 1}, "extra"), ([], "perms")],
)
def test_a_non_string_column_is_refused(value: object, column: str) -> None:
    """Every column is a JSON string in the six-column contract. A non-string reaches the
    matcher as-is: a null `id` raises TypeError inside its regex and ends the scan."""
    bad = row()
    bad[column] = value  # type: ignore[assignment]
    env = read(frame([bad]))
    assert env.outcome is EnvelopeOutcome.MALFORMED
    assert column in (env.detail or "")


def test_deeply_nested_json_is_malformed_rather_than_a_recursion_error() -> None:
    """Cheap to write, and it would otherwise escape read() and end the scan."""
    depth = 200_000
    env = read(FRAME_PREFIX + base64.b64encode(_gz(("[" * depth).encode())).decode())
    assert env.outcome is EnvelopeOutcome.MALFORMED


def _gz(raw: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(raw)
    return buf.getvalue()
