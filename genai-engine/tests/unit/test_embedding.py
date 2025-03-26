from unittest.mock import patch

import pytest
from chat.embedding import EmbeddingModel
from langchain_openai import AzureOpenAIEmbeddings


@patch.object(AzureOpenAIEmbeddings, "__init__", lambda *args, **kwargs: None)
@patch.object(AzureOpenAIEmbeddings, "embed_query", lambda *args: ["0.1", "0.2"])
@pytest.mark.unit_tests
def test_embed_query():
    # Initialize the EmbeddingModel
    model = EmbeddingModel()

    # Test the embed_query method
    query = "How to test a class in Python?"
    expected_output = ["0.1", "0.2"]
    assert model.embed_query(query) == expected_output
