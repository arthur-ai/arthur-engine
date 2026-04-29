"""Token-aware chunkers.

Migrated verbatim from genai-engine/src/utils/text_chunking.py.

ChunkIterator: word-level chunker that yields up to `chunk_size` tokens per
chunk while never splitting a word across chunks. Used by the toxicity and
PII pipelines to break long inputs into model-sized pieces.

SlidingWindowChunkIterator: sliding-window variant with configurable stride.
Used by prompt injection (chunk_size=512, stride=256) to give the classifier
overlapping looks at the prompt without splitting words.
"""

from transformers import PreTrainedTokenizerBase


class ChunkIterator:
    """Word-level chunker — yields up to chunk_size tokens, never splitting words."""

    def __init__(
        self,
        text: str,
        tokenizer: PreTrainedTokenizerBase,
        chunk_size: int,
    ) -> None:
        self.tokenizer = tokenizer
        self.chunk_size = chunk_size
        self.text = text
        self._setup()

    def _setup(self) -> None:
        encoding = self.tokenizer(
            self.text,
            return_offsets_mapping=True,
            add_special_tokens=False,
        )
        self.token_ids = encoding["input_ids"]
        self.offsets = encoding["offset_mapping"]
        self.word_ids = encoding.word_ids()
        self.prev_char = 0
        self.i = 0

    def __iter__(self) -> "ChunkIterator":
        return self

    def __next__(self) -> str:
        if self.i >= len(self.token_ids) or self.chunk_size <= 0:
            raise StopIteration

        j = min(self.i + self.chunk_size, len(self.token_ids))

        # Backtrack to a word boundary.
        while (
            j < len(self.token_ids)
            and j > self.i
            and self.word_ids[j] is not None
            and self.word_ids[j - 1] == self.word_ids[j]
        ):
            j -= 1

        if j == self.i:
            j = min(self.i + self.chunk_size, len(self.token_ids))

        end_char = self.offsets[j - 1][1]
        if j == len(self.token_ids):
            end_char = len(self.text)

        chunk = self.text[self.prev_char:end_char]
        self.prev_char = end_char
        self.i = j
        return chunk


class SlidingWindowChunkIterator:
    """Sliding-window word-level chunker. Used by prompt injection (chunk_size=512, stride=256)."""

    def __init__(
        self,
        text: str,
        tokenizer: PreTrainedTokenizerBase,
        chunk_size: int,
        stride: int = 1,
    ) -> None:
        self.text = text
        self.tokenizer = tokenizer
        self.chunk_size = max(chunk_size, 1)
        self.stride = self.chunk_size if stride < 1 else min(stride, self.chunk_size)
        self.index = 0
        self.last_end = 0
        self.got_full = False
        self.got_tail = False
        self._setup()

    def _setup(self) -> None:
        encoding = self.tokenizer(
            self.text,
            return_offsets_mapping=True,
            add_special_tokens=False,
        )
        offsets = encoding["offset_mapping"]
        word_ids = encoding.word_ids()

        self.word_spans: list[list[int]] = []
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

    def __iter__(self) -> "SlidingWindowChunkIterator":
        return self

    def __next__(self) -> str:
        if self.num_words == 0 or self.chunk_size <= 0:
            raise StopIteration

        if self.chunk_size >= self.num_words:
            if not self.got_full:
                self.got_full = True
                return self.text
            raise StopIteration

        if self.index <= self.num_words - self.chunk_size:
            start_char = self.word_spans[self.index][0]
            end_char = self.word_spans[self.index + self.chunk_size - 1][1]
            chunk = self.text[start_char:end_char]
            self.last_end = self.index + self.chunk_size
            self.index += self.stride
            return chunk

        if not self.got_tail and self.last_end < self.num_words:
            start_char = self.word_spans[self.last_end][0]
            end_char = self.word_spans[-1][1]
            self.got_tail = True
            return self.text[start_char:end_char]

        raise StopIteration
