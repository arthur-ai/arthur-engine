import logging
import re
import string

import commonmark
from commonmark.node import Node
from nltk.tokenize.punkt import PunktSentenceTokenizer

from utils.abbreviations import ABBREVIATIONS
from utils.utils import list_indicator_regex

SENTENCE_TOKENIZER = PunktSentenceTokenizer()
LOGGER = logging.getLogger()


class ClaimParser:
    def __init__(self) -> None:
        self.parser = commonmark.Parser()

    def _deduplicate(self, seq: list[str]) -> list[str]:
        """
        Source: https://stackoverflow.com/a/480227/1493011
        """

        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]

    def _strip_markdown(self, text: str) -> str:
        """
        Strip Markdown from a LLM Response
        """

        def ast2text(astNode: Node) -> str:
            """
            Returns the text from markdown, stripped of the markdown syntax itself
            """
            walker = astNode.walker()
            acc = ""
            iterator = iter(walker)
            list_level = 0
            for current, entering in iterator:
                if current.literal and not (
                    current.parent
                    and current.parent.t == "link"
                    and current.parent.destination == current.literal
                ):
                    # workaround for list items that are not formatted as proper markdown
                    if (
                        list_indicator_regex.match(current.literal.strip())
                        and list_level <= 1
                    ):
                        acc += "\n"
                    acc += current.literal
                if current.t == "linebreak":
                    acc += "\n"
                elif current.t == "softbreak":
                    acc += " "
                elif current.t == "list" and entering:
                    if list_level > 0:
                        # Already in a list
                        acc = acc.strip() + " "
                        # Sub the last new line, the rest of the item is supposed to be on the same line
                    list_level += 1
                elif current.t == "list" and not entering:
                    list_level -= 1
                    if list_level <= 1:
                        acc = acc.strip()
                        acc += "\n"
                elif current.t == "paragraph" and not entering:
                    if list_level > 1:
                        if acc[-1] in string.punctuation:
                            acc = acc[:-1]  # Strip punctuation for list items
                        acc += " "  # Don't add new line until exiting nested alist
                    else:
                        acc = acc.strip()
                        acc += "\n"
                elif current.t == "heading" and not entering:
                    acc += " "
                elif current.t in ("link", "image") and entering is False:
                    acc += f" {current.destination}"
                    if current.title:
                        acc += f" - {current.title}"
            return acc.strip()

        try:
            ast = self.parser.parse(text)
            parsed = ast2text(ast)
        except Exception as e:
            parsed = text
            LOGGER.warning(f"Failed to parse text with exception {e}")

        return parsed

    def process_and_extract_claims(self, text: str | None) -> list[str]:
        """
        Returns a list of texts that should contain sentences & list items from an LLM response
        """
        # check for the edge case where the text is just a singular digit or letter and skip strip_markdown
        # if it is to avoid the function from mistaking it for a list item
        if text is None:
            return []
        if not re.match(r"^(?:\d+|[A-Za-z])\.?\s*$", text.strip()):
            text = self._strip_markdown(text)

        abbreviation_pattern = r"([A-Za-z]\.)([A-Za-z]\.)+"
        all_abbreviations = re.finditer(abbreviation_pattern, text)

        # Iterate through all found emails and replace .com
        for abbrev in all_abbreviations:
            found = abbrev.group(0)
            text = text.replace(found, found.replace(".", ""))

        for s in ABBREVIATIONS:
            text = text.replace(s, s.replace(".", ""))

        lines = text.strip().split("\n")
        texts = []
        for line in lines:
            line = line.strip()
            if list_indicator_regex.match(line.strip()):
                texts.append(line.strip())
            else:
                texts.extend(SENTENCE_TOKENIZER.tokenize(line))

        return self._deduplicate(texts)
