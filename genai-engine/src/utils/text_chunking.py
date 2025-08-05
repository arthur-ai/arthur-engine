class ChunkIterator:
    """
    Iterator class for chunking a text at the word level

    Args:
        text: The input text to be chunked
        tokenizer: The tokenizer used to extract encodings
        chunk_size: Maximum number of word tokens per chunk
    """

    def __init__(self, text, tokenizer, chunk_size):
        self.tokenizer = tokenizer
        self.chunk_size = chunk_size
        self.text = text

        self.setup_text()

    def __iter__(self):
        return self

    def setup_text(self):
        """
        Sets up necessary variables used for chunking by:
         - tokenizing the input text
         - extracting token IDs, offset mappings, and word IDs
         - initializing tracking variables
        """
        encoding = self.tokenizer(
            self.text,
            return_offsets_mapping=True,
            add_special_tokens=False,
        )

        # the IDs for each token in the text
        self.token_ids = encoding["input_ids"]

        # char positions for each token
        self.offsets = encoding["offset_mapping"]

        # map for tokens to word positions
        self.word_ids = encoding.word_ids()

        self.prev_char = 0
        self.i = 0

        return self

    def __next__(self):
        """
        Extracts and returns the next chunk of text

        Returns:
            str: The next chunk of text
        """
        # check if we've processed all tokens
        if self.i >= len(self.token_ids) or self.chunk_size <= 0:
            raise StopIteration

        # get the end position for this chunk
        j = min(self.i + self.chunk_size, len(self.token_ids))

        # backtrack to avoid splitting words between chunks
        while (
            j < len(self.token_ids)
            and j > self.i
            and self.word_ids[j] is not None
            and self.word_ids[j - 1] == self.word_ids[j]
        ):
            j -= 1

        # fallback to force progress if no word boundary was found
        # Note: will cutoff words mid-word
        if j == self.i:
            j = min(self.i + self.chunk_size, len(self.token_ids))

        # get the ending char for this chunk
        end_char = self.offsets[j - 1][1]
        if j == len(self.token_ids):
            end_char = len(self.text)

        # extract chunk and update iter vars
        chunk = self.text[self.prev_char : end_char]
        self.prev_char = end_char
        self.i = j

        return chunk


class SlidingWindowChunkIterator:
    """
    Iterator class for sliding-window chunking at the word level, preserving full words.

    Args:
        text: The input text to be chunked
        tokenizer: The tokenizer used to extract encodings
        chunk_size: Number of words per chunk
        stride: Number of words to advance for each new chunk (defaults to chunk_size)
    """

    def __init__(self, text, tokenizer, chunk_size, stride=1):
        self.text = text
        self.tokenizer = tokenizer
        self.chunk_size = max(chunk_size, 1)
        self.stride = self.chunk_size if stride < 1 else min(stride, self.chunk_size)
        self.index = 0
        self.last_end = 0
        self.got_full = False
        self.got_tail = False
        self.setup_text()

    def __iter__(self):
        return self

    def setup_text(self):
        encoding = self.tokenizer(
            self.text,
            return_offsets_mapping=True,
            add_special_tokens=False,
        )
        offsets = encoding["offset_mapping"]
        word_ids = encoding.word_ids()

        # build a list of (start, end) spans for each full word
        self.word_spans = []
        prev_wid = None
        for (start, end), wid in zip(offsets, word_ids):
            if wid is None:
                continue
            if wid != prev_wid:
                self.word_spans.append([start, end])
                prev_wid = wid
            else:
                self.word_spans[-1][1] = end

        self.num_words = len(self.word_spans)
        return self

    def __next__(self):
        # nothing to chunk
        if self.num_words == 0 or self.chunk_size <= 0:
            raise StopIteration

        # single-chunk case
        if self.chunk_size >= self.num_words:
            if not self.got_full:
                self.got_full = True
                return self.text
            raise StopIteration

        # full-word windows
        if self.index <= self.num_words - self.chunk_size:
            start_char = self.word_spans[self.index][0]
            end_char = self.word_spans[self.index + self.chunk_size - 1][1]
            chunk = self.text[start_char:end_char]

            # track where this chunk ended
            self.last_end = self.index + self.chunk_size
            self.index += self.stride
            return chunk

        # leftover tail: fewer than chunk_size words remain
        if not self.got_tail and self.last_end < self.num_words:
            start_char = self.word_spans[self.last_end][0]
            end_char = self.word_spans[-1][1]
            self.got_tail = True
            return self.text[start_char:end_char]

        # done
        raise StopIteration
