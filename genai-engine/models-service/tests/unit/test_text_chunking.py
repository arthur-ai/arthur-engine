"""Text-chunking unit tests.

Migrated verbatim from genai-engine/tests/unit/utils/test_text_chunking.py.
Marked `real_models` because we use the prompt-injection tokenizer; if the
weights aren't loaded, the fixture is skipped.
"""

import pytest

from inference.text_chunking import ChunkIterator, SlidingWindowChunkIterator

pytestmark = pytest.mark.real_models


@pytest.fixture(scope="module")
def tokenizer():
    from models import loader

    tok = loader.get_prompt_injection_tokenizer()
    if tok is None:
        pytest.skip("Prompt-injection tokenizer not loaded")
    return tok


# ------------------------------- ChunkIterator ----------------------------


@pytest.mark.parametrize(
    "text, expected_chunks, chunk_size",
    [
        ("", [], 5),
        ("@@@ ### $$$", ["@@", "@", " ##", "#", " $$", "$"], 2),
        ("aaaaaaaaaaaaaaaaaaaaa", ["aaaaaaaaaaaaaaaaaaaaa"], 5),
        (
            "Tokennn boundarieees arrre respeccccted.",
            ["Tokennn", " boundarieees", " arrre", " respecccc", "ted."],
            3,
        ),
        (
            "Token boundaries are respected.",
            ["Token boundaries are", " respected."],
            3,
        ),
    ],
)
def test_token_boundaries(tokenizer, text, expected_chunks, chunk_size):
    chunks = list(ChunkIterator(text, tokenizer, chunk_size))
    assert chunks == expected_chunks
    assert "".join(chunks) == text


def test_single_chunk_exact_fit(tokenizer):
    chunks = list(ChunkIterator("A short sentence.", tokenizer, 100))
    assert chunks == ["A short sentence."]


def test_chunk_size_zero_no_text(tokenizer):
    assert list(ChunkIterator("", tokenizer, 0)) == []


def test_chunk_size_zero(tokenizer):
    assert list(ChunkIterator("This string should be ignored", tokenizer, 0)) == []


# ------------------------- SlidingWindowChunkIterator ---------------------


@pytest.mark.parametrize(
    "text, chunk_size, stride, expected_count",
    [
        ("Hello.", 2, 1, 1),
        ("This is exactly four words.", 4, 2, 2),
        ("The quick brown fox jumps over the lazy dog near the riverbank.", 5, 2, 5),
        ("Wait! Are you coming? No, I can't. Sorry.", 3, 1, 6),
        ("", 3, 1, 0),
        ("     ", 2, 1, 0),
        ("word " * 1200, 512, 256, 4),
        ("a" * 500, 3, 1, 1),
        ("Too short.", 10, 5, 1),
        ("Chunks do not overlap in this configuration.", 3, 3, 3),
        ("Should handle zero chunk size.", 0, 1, 5),
        ("Negative stride should not break iterator.", 2, -1, 3),
    ],
)
def test_sliding_window_counts(tokenizer, text, chunk_size, stride, expected_count):
    chunks = list(SlidingWindowChunkIterator(
        text=text,
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        stride=stride,
    ))
    assert len(chunks) == expected_count


@pytest.mark.parametrize(
    "text, chunk_size, stride, expected",
    [
        ("Hello.", 2, 1, ["Hello."]),
        ("This is exactly four words.", 4, 2, ["This is exactly four", " words."]),
        (
            "The quick brown fox jumps over the lazy dog near the riverbank.",
            5,
            2,
            [
                "The quick brown fox jumps",
                " brown fox jumps over the",
                " jumps over the lazy dog",
                " the lazy dog near the",
                " riverbank.",
            ],
        ),
        ("", 3, 1, []),
        ("?!...!!!,,,;", 3, 1, ["?!...!!!,,,;"]),
        (
            "Chunks do not overlap in this configuration.",
            3,
            3,
            ["Chunks do not", " overlap in this", " configuration."],
        ),
    ],
)
def test_sliding_window_exact(tokenizer, text, chunk_size, stride, expected):
    chunks = list(SlidingWindowChunkIterator(
        text=text,
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        stride=stride,
    ))
    assert chunks == expected
