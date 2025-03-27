import tiktoken

TIKTOKEN_ENCODER = "cl100k_base"


class TokenCounter:
    def __init__(self, model: str = TIKTOKEN_ENCODER):
        """Initializes a titoken encoder

        :param model: tiktoken model encoder
        """
        self.encoder = tiktoken.get_encoding(model)

    def count(self, query: str):
        """returns token count of the query

        :param query: string query sent to LLM
        """
        return len(self.encoder.encode(query))
