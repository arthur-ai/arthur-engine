"""Regex-based profanity detection.

Migrated from genai-engine/src/scorer/checks/toxicity/toxicity_profanity/profanity.py.
The blacklist + end-punctuations data files sit alongside this module.

Builds an obscured-word regex per blacklist entry: each letter expands to a
character class covering common substitutions ("f*ck", "sh!t", "a55"). The
patterns require word boundaries so spaced-out forms like "s h i t" are not
matched.

detect_profanity(s) returns the matched substring on hit (so callers can
surface it for telemetry) or None on miss. The original engine signature
returned bool; the matched string is a strict superset of that information
since callers can `bool(detect_profanity(...))`.
"""

import os
import re

__location__ = os.path.dirname(os.path.abspath(__file__))

BLACKLIST_PATH = os.path.join(__location__, "profanity_blacklist.txt")

with open(BLACKLIST_PATH, "r") as _f:
    FULLY_BAD_WORDS: set[str] = set(_f.read().splitlines())


# Map letters to common substitution character classes (e.g. f*ck, sh!t, a55).
letter_substitutions = {
    "a": "[a@4*]", "b": "[b8]",  "c": "[c(]",  "d": "[d]",
    "e": "[e3*]", "f": "[f]",   "g": "[g9]",  "h": "[h#]",
    "i": "[i!1*]","j": "[j]",   "k": "[k]",   "l": "[l1]",
    "m": "[m]",   "n": "[n]",   "o": "[o0*]", "p": "[p]",
    "q": "[q]",   "r": "[r]",   "s": "[s$5]", "t": "[t+]",
    "u": "[u*]",  "v": "[v]",   "w": "[w]",   "x": "[x]",
    "y": "[y*]",  "z": "[z2]",
}


def _generate_obscured_regex(word: str) -> re.Pattern[str]:
    """Build a regex that matches `word` with single-char substitutions but
    no whitespace or repeated obscuring (so 'sh*t' matches but 's h i t' doesn't)."""
    pattern = r"(?<!\w)"  # not preceded by word char
    pattern += "".join(
        rf"(?:{letter_substitutions.get(c, re.escape(c))})" for c in word
    )
    pattern += r"(?!\w)"  # not followed by word char
    return re.compile(pattern, flags=re.IGNORECASE)


_all_bad_word_regexes: list[re.Pattern[str]] = [
    _generate_obscured_regex(w) for w in FULLY_BAD_WORDS
]


def detect_profanity(s: str) -> str | None:
    """Search `s` for any blacklisted word (with substitutions). Returns the
    matched substring (from the lowercased input) on hit, None otherwise."""
    s_lower = s.lower()
    for reg in _all_bad_word_regexes:
        m = reg.search(s_lower)
        if m:
            return m.group(0)
    return None
