import pytest
from repositories.embedding_repository import chunk_text


@pytest.mark.parametrize(
    "words,chunk_size,expected_output",
    [
        (["word1", "word2", "word3", "word4"], 2, ["word1 word2", "word3 word4"]),
        (
            ["word1", "word2", "word3", "word4", "word5"],
            3,
            ["word1 word2 word3", "word4 word5"],
        ),
        (["word1", "word2", "word3", "word4"], 1, ["word1", "word2", "word3", "word4"]),
        (["word1", "word2"], 5, ["word1 word2"]),
        ([], 3, []),
    ],
)
@pytest.mark.unit_tests
def test_chunk_text(words, chunk_size, expected_output):
    result = chunk_text(words, chunk_size)
    assert result == expected_output
