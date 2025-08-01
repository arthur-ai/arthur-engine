import os

import pytest
from transformers import AutoTokenizer

from utils.text_chunking import ChunkIterator, SlidingWindowChunkIterator

CLASSIFIER_PATH = "shield/scorer/checks/toxicity/toxicity_deberta_classifier"
TOXICITY_CLASSIFIER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../..",
    CLASSIFIER_PATH,
)

tokenizer = AutoTokenizer.from_pretrained(TOXICITY_CLASSIFIER_PATH)


@pytest.mark.parametrize(
    "text, actual_chunks, chunk_size",
    [
        ("", [], 5),  # test empty string
        ("@@@ ### $$$", ["@@", "@", " ##", "#", " $$", "$"], 2),  # test no actual words
        (
            "aaaaaaaaaaaaaaaaaaaaa",
            ["aaaaaaaaaaaaaaaaaaaaa"],
            5,
        ),  # test one letter repeated
        (
            "Tokennn boundarieees arrre respeccccted.",
            ["Tokennn", " boundarieees", " arrre", " respecccc", "ted."],
            3,
        ),  # test messed up words
        (
            "Token boundaries are respected.",
            ["Token boundaries are", " respected."],
            3,
        ),  # test splitting at word level
    ],
)
@pytest.mark.unit_tests
def test_token_boundaries(text, actual_chunks, chunk_size):
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    print(chunks)

    assert len(chunks) == len(actual_chunks)
    assert "".join(chunks) == text

    for i, chunk in enumerate(chunks):
        assert chunk == actual_chunks[i]


# test a chunk size large enough to fit the whole text
@pytest.mark.unit_tests
def test_single_chunk_exact_fit():
    text = "A short sentence."
    chunk_size = 100
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    assert len(chunks) == 1
    assert chunks[0] == text


# test a chunk size that is too small to fit the whole text
@pytest.mark.unit_tests
def test_chunking_last_chunk_smaller():
    text = "One two three four five six"
    chunk_size = 4
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    assert len(chunks) >= 2
    assert sum(len(c.split()) for c in chunks) == len(text.split())


@pytest.mark.unit_tests
def test_exact_boundary_chunking():
    text = "One two three four five six"
    chunk_size = 3  # exactly splits into 2 chunks of 3 words each
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    assert "".join(chunks) == text
    assert len(chunks) == 2
    assert chunks[0].endswith("three")
    assert chunks[1].startswith(" four")


# test large words are kept whole
@pytest.mark.unit_tests
def test_multi_subword_split():
    text = "unbelievable misinterpretation"
    chunk_size = 1
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    assert len(chunks) == 2
    assert "unbelievable" in chunks[0]
    assert "misinterpretation" in chunks[1]


# test chunk size of 1
@pytest.mark.unit_tests
def test_chunk_size_one():
    text = "A B C D"
    chunk_size = 1
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    assert len(chunks) == 4
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")


# test chunk size of 0 with empty string
@pytest.mark.unit_tests
def test_chunk_size_zero_no_text():
    text = ""
    chunk_size = 0
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    assert len(chunks) == 0
    assert chunks == []
    assert "".join(chunks) == text


# test chunk size of 0 with non-empty string
@pytest.mark.unit_tests
def test_chunk_size_zero():
    text = "This string should be ignored"
    chunk_size = 0
    iterator = ChunkIterator(text, tokenizer, chunk_size)
    chunks = list(iterator)

    assert len(chunks) == 0
    assert chunks == []
    assert "".join(chunks) != text


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "text, chunk_size, stride, actual_num_chunks",
    [
        ("Hello.", 2, 1, 1),
        ("This is exactly four words.", 4, 2, 2),
        ("The quick brown fox jumps over the lazy dog near the riverbank.", 5, 2, 5),
        ("Wait! Are you coming? No, I can't. Sorry.", 3, 1, 6),
        ("I love pizza 🍕, and parties 🎉 are the best!", 4, 2, 4),
        ("User123 logged in at 9:00am on 07/29/2025.\nStatus: ✅\n", 3, 1, 7),
        (
            "Artificial intelligence is transforming industries by enabling machines to learn from data, make decisions, and automate tasks. As AI systems become more prevalent, it is important to address concerns around fairness, transparency, and accountability to ensure that these technologies benefit society as a whole.",
            10,
            5,
            8,
        ),
        ("", 3, 1, 0),
        ("     ", 2, 1, 0),
        ("word " * 1200, 512, 256, 4),
        ("a" * 500, 3, 1, 1),
        ("def foo():\n    return 'bar'\n# end", 2, 1, 5),
        ("Column1\tColumn2\tColumn3", 2, 1, 2),
        ("?!...!!!,,,;", 3, 1, 1),
        ("This is a sentence for chunking.", 1, 1, 6),
        ("Too short.", 10, 5, 1),
        ("overlapping chunks are common in NLP tasks.", 3, 1, 5),
        ("Chunks do not overlap in this configuration.", 3, 3, 3),
        ("Stride set to zero, should match chunk size jump.", 4, 0, 3),
        ("Should handle zero chunk size.", 0, 1, 5),
        ("Negative stride should not break iterator.", 2, -1, 3),
        ("Almost all words in one chunk here.", 6, 2, 2),
        ("Small sample.", len("Small sample."), 1, 1),
        ("One two three four five six seven eight nine ten", 3, 1, 8),
        ("One two three four five six seven eight nine ten", 3, 2, 5),
        ("a b c d e f g h i j k l m n o p", 4, 4, 4),
        ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu", 3, 5, 4),
        ("single word chunks only please now yes go", 1, 1, 8),
        ("this is a rolling window over bigrams", 2, 1, 6),
        ("pairs of words are grouped together here", 2, 2, 4),
        (" ".join([f"w{i}" for i in range(40)]), 5, 2, 19),
        (" ".join([f"word{i}" for i in range(25)]), 10, 9, 3),
        (" ".join([f"data{i}" for i in range(30)]), 4, 6, 8),
        ("one two three four five six seven eight nine", 4, 3, 3),
        ("Hello, world! How are you today? Testing, one two three.", 3, 1, 8),
        ("😀 😃 😄 😁 😆 😅 😂 🤣 🥲 ☺️ 😊 😇 🙂 🙃 😉", 4, 2, 7),
        ("alpha beta gamma delta epsilon zeta eta theta", 4, 2, 3),
        ("a b c d e f g", 6, 2, 2),
        ("x y z a b c d e f g", 3, 15, 4),
        ("too few words for large chunk", 100, 1, 1),
        ("zero stride is really just chunk size jump", 2, 0, 4),
        ("negative stride should not break code", 2, -3, 3),
        ("should handle zero chunk size", 0, 1, 5),
    ],
)
def test_sliding_window_chunk_sizes(text, chunk_size, stride, actual_num_chunks):
    iterator = SlidingWindowChunkIterator(
        text=text,
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        stride=stride,
    )

    chunks = list(iterator)

    assert len(chunks) == actual_num_chunks


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "text, chunk_size, stride",
    [
        ("Hello.", 2, 1),
        ("This is exactly four words.", 4, 2),
        ("The quick brown fox jumps over the lazy dog near the riverbank.", 5, 5),
        ("Wait! Are you coming? No, I can't. Sorry.", 3, 3),
        ("I love pizza 🍕, and parties 🎉 are the best!", 0, 0),
        ("User123 logged in at 9:00am on 07/29/2025.\nStatus: ✅\n", 100, 1),
        ("", 3, 1),
        ("a" * 500, 3, 1),
        ("This is a sentence for chunking.", 1, 20),
        ("should handle zero chunk size", 0, 1),
    ],
)
def test_sliding_window_same_text(text, chunk_size, stride):
    iterator = SlidingWindowChunkIterator(
        text=text,
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        stride=stride,
    )

    chunks = list(iterator)

    assert "".join(chunks) == text


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "text, chunk_size, stride, actual_chunks",
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
        (
            "Wait! Are you coming? No, I can't. Sorry.",
            3,
            1,
            [
                "Wait! Are you",
                " Are you coming?",
                " you coming? No,",
                " coming? No, I",
                " No, I can't.",
                " I can't. Sorry.",
            ],
        ),
        (
            "I love pizza 🍕, and parties 🎉 are the best!",
            4,
            2,
            [
                "I love pizza 🍕,",
                " pizza 🍕, and parties",
                " and parties 🎉 are",
                " 🎉 are the best!",
            ],
        ),
        (
            "User123 logged in at 9:00am on 07/29/2025.\nStatus: ✅\n",
            3,
            1,
            [
                "User123 logged in",
                " logged in at",
                " in at 9:00am",
                " at 9:00am on",
                " 9:00am on 07/29/2025.",
                " on 07/29/2025.\nStatus:",
                " 07/29/2025.\nStatus: ✅",
            ],
        ),
        ("", 3, 1, []),
        ("     ", 2, 1, []),
        ("?!...!!!,,,;", 3, 1, ["?!...!!!,,,;"]),
        (
            "This is a sentence for chunking.",
            1,
            1,
            ["This", " is", " a", " sentence", " for", " chunking."],
        ),
        ("Too short.", 10, 5, ["Too short."]),
        (
            "overlapping chunks are common in NLP tasks.",
            3,
            1,
            [
                "overlapping chunks are",
                " chunks are common",
                " are common in",
                " common in NLP",
                " in NLP tasks.",
            ],
        ),
        (
            "Chunks do not overlap in this configuration.",
            3,
            3,
            ["Chunks do not", " overlap in this", " configuration."],
        ),
        (
            "Stride set to zero, should match chunk size jump.",
            4,
            0,
            ["Stride set to zero,", " should match chunk size", " jump."],
        ),
        (
            "Should handle zero chunk size.",
            0,
            1,
            ["Should", " handle", " zero", " chunk", " size."],
        ),
        (
            "Negative stride should not break iterator.",
            2,
            -1,
            ["Negative stride", " should not", " break iterator."],
        ),
    ],
)
def test_sliding_window_chunking(text, chunk_size, stride, actual_chunks):
    iterator = SlidingWindowChunkIterator(
        text=text,
        tokenizer=tokenizer,
        chunk_size=chunk_size,
        stride=stride,
    )

    chunks = list(iterator)

    assert len(chunks) == len(actual_chunks)

    for i, chunk in enumerate(chunks):
        assert chunk == actual_chunks[i]
