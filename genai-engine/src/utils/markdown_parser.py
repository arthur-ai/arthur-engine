import commonmark
import re
import string
from utils.abbreviations import ABBREVIATIONS
from utils.utils import sentence_tokenizer, list_indicator_regex, logger

class MarkdownParser:
    def __init__(self):
        self.parser = commonmark.Parser()

    def deduplicate(self, seq: list[str]) -> list[str]:
        """
        Source: https://stackoverflow.com/a/480227/1493011
        """

        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    def strip_markdown(self, text: str) -> str:
        """
        Strip Markdown from a LLM Response
        """
        def ast2text(astNode):
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
            logger.warning(f"Failed to parse text with exception {e}")

        return parsed

    def parse_markdown(self, text) -> list[str]:
        """
        Returns a list of texts that should contain sentences & list items from an LLM response
        """
        text = self.strip_markdown(text)
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
                texts.extend(sentence_tokenizer.tokenize(line))

        return self.deduplicate(texts)