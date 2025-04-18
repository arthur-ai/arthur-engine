import json
import os
import re

__location__ = os.path.dirname(os.path.abspath(__file__))

FULLY_BAD_WORDS_PATH = "level_1_words.jsonl"
END_PUNCTUATIONS_PATH = "end_punctuations.jsonl"

with open(os.path.join(__location__, FULLY_BAD_WORDS_PATH), "r") as file:
    FULLY_BAD_WORDS = [json.loads(line)["text"] for line in file]

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


def generate_obscured_regex(word, block_all_prefix=True, block_all_suffix=True):
    """Generates a regex to detect a word, including attempted obscured representations of the word

    Arguments:
        word: str
    Returns:
        regex pattern catching direct & obscured representations of the word

    Example:
        >>> reg = generate_obscured_regex('shit')
        >>> re.search(reg, 's,h  ! t')
        <re.Match object; span=(0, 8), match='s,h  ! t'>
    """
    if block_all_prefix:
        pattern = r"("
    else:
        pattern = r"(?:^|\W)("
    pattern += r"\W*".join(
        [
            rf"(?:{letter_substitutions.get(char, re.escape(char))}+\W*)"
            for char in word
        ],
    )
    if block_all_suffix:
        pattern += r")"
    else:
        pattern += r"(?=$|\W))"

    return re.compile(pattern)


# use the above function to generate an obscured regex to catch
# obscured representations of the profanities in the local json files
all_bad_word_regexes = [generate_obscured_regex(w) for w in FULLY_BAD_WORDS]


def detect_profanity(s):
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
