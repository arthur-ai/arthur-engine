import json
import os
import re

__location__ = os.path.dirname(os.path.abspath(__file__))

FULLY_BAD_WORDS_PATH = "profanity_blacklist.txt"
END_PUNCTUATIONS_PATH = "end_punctuations.jsonl"

with open(os.path.join(__location__, FULLY_BAD_WORDS_PATH), "r") as file:
    FULLY_BAD_WORDS = set(file.read().splitlines())

with open(os.path.join(__location__, END_PUNCTUATIONS_PATH), "r") as file:
    END_PUNCTUATIONS = [json.loads(line)["text"] for line in file]


letter_substitutions = {
    "a": "[a@4*]",
    "b": "[b8]",
    "c": "[c(]",
    "d": "[d]",
    "e": "[e3*]",
    "f": "[f]",
    "g": "[g9]",
    "h": "[h#]",
    "i": "[i!1*]",
    "j": "[j]",
    "k": "[k]",
    "l": "[l1]",
    "m": "[m]",
    "n": "[n]",
    "o": "[o0*]",
    "p": "[p]",
    "q": "[q]",
    "r": "[r]",
    "s": "[s$5]",
    "t": "[t+]",
    "u": "[u*]",
    "v": "[v]",
    "w": "[w]",
    "x": "[x]",
    "y": "[y*]",
    "z": "[z2]",
}


def generate_obscured_regex(word: str) -> re.Pattern[str]:
    """
    Generates a regex to match a standalone word with allowed character substitutions (e.g. f*ck, sh!t, or a55),
    but it does not check for multiple substitutions or spaces (e.g. 's h i t' and 'f***ck' would not be flagged)

    Arguments:
        word: str

    Returns:
        compiled regex pattern
    """

    # check this word is not preceded by a word character
    pattern = r"(?<!\w)"

    # check for possible single-letter subsitutions in a word
    pattern += "".join(
        rf"(?:{letter_substitutions.get(c, re.escape(c))})" for c in word
    )

    # check this word is not followed by a word character
    pattern += r"(?!\w)"

    return re.compile(pattern, flags=re.IGNORECASE)


# use the above function to generate an obscured regex to catch
# obscured representations of the profanities in the local blacklist
all_bad_word_regexes: list[re.Pattern[str]] = [
    generate_obscured_regex(w) for w in FULLY_BAD_WORDS
]


def detect_profanity(s: str) -> bool:
    """
    Detects profanity using the regular expressions generated above

    Arguments:
        s: str
    Returns:
        bool indicating whether s contains a representation of profanity
    """
    s = s.lower()
    for reg in all_bad_word_regexes:
        if reg.search(s):
            return True
    return False
