"""Cap on variable values stored with a continuous eval run.

The judge always sees the full value; only the copy kept on the run row
(agentic_annotations.input_variables) is cut. An 'all' value joins every matching
span and can grow with the trace, and in span scope it is stored once per span run.
"""

import hashlib

STORED_VALUE_MAX_CHARS = 8_000


def cap_stored_value(value: str, max_chars: int = STORED_VALUE_MAX_CHARS) -> str:
    """Keep the head and tail of a long value, joined by a marker that says how much
    was cut and carries the full value's sha256 and length, so a rerun can prove it
    judged the same text. Values within max_chars come back unchanged."""
    if len(value) <= max_chars:
        return value
    digest = hashlib.sha256(value.encode()).hexdigest()

    def marker(cut: int) -> str:
        return f"\n[cut {cut} chars, sha256={digest}, len={len(value)}]\n"

    # Size the marker for the largest possible cut, so the result never exceeds
    # max_chars once the real (smaller or equal) cut is filled in.
    budget = max(0, max_chars - len(marker(len(value))))
    head = budget // 2
    tail = budget - head
    cut = len(value) - head - tail
    return value[:head] + marker(cut) + (value[-tail:] if tail else "")
