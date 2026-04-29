"""Small text helpers used by the toxicity scorer.

Migrated from genai-engine/src/utils/utils.py.

list_indicator_regex: matches list-marker prefixes ("-", "•", "*", "1)",
"1.") so the section-splitter can keep list items intact instead of
fragmenting them.

pad_text: pads strings (or each string in a list) up to a minimum length.
The RoBERTa toxicity classifier was fine-tuned almost exclusively on inputs
≥20 chars, so short inputs are padded to avoid a known low-coverage region
of the model.
"""

import re
from typing import TypeVar

list_indicator_regex = re.compile(r"^[\-\•\*]|\d+\)|\d+\.")

T = TypeVar("T", str, list[str])


def pad_text(
    text: T,
    min_length: int = 20,
    delim: str = " ",
    pad_type: str = "whitespace",
) -> T:
    """Pad text (or list of texts) up to min_length. The toxicity classifier
    was fine-tuned on inputs ≥20 chars, so short inputs need padding to avoid
    a known model bug (see toxicity.py:206-207 in genai-engine)."""
    if isinstance(text, list):
        return [
            pad_text(item, min_length=min_length, pad_type=pad_type) for item in text
        ]
    while len(text) < min_length:
        if pad_type == "whitespace":
            text = text + delim
        elif pad_type == "repetition":
            text = text + text + delim
    return text
