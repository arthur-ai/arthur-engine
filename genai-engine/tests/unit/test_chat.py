from unittest.mock import MagicMock, Mock, patch

import pytest
from chat.chat import ArthurChat
from schemas.internal_schemas import Embedding

BASIC_MOCK_INFERENCES = (
    [
        Mock(
            inference_prompt=Mock(message="word word1"),
            inference_response=Mock(message="word word2"),
        ),
    ],
    10,
)
BASIC_MOCK_CURLY_BRACKETS = (
    [
        Mock(
            inference_prompt=Mock(message="word {word1}"),
            inference_response=Mock(message="word {word2}"),
        ),
        Mock(
            inference_prompt=Mock(message="word {{word3}}"),
            inference_response=Mock(message="word {{word4}}"),
        ),
    ],
    10,
)
BASIC_MOCK_OVERFLOW = (
    [
        Mock(
            inference_prompt=Mock(message="word word1"),
            inference_response=Mock(message="word word2"),
        ),
        Mock(
            inference_prompt=Mock(message="word word1"),
            inference_response=Mock(message="word word2"),
        ),
        Mock(
            inference_prompt=Mock(message="word word1"),
            inference_response=Mock(message="word word2"),
        ),
        Mock(
            inference_prompt=Mock(message="word word1"),
            inference_response=Mock(message="word word2"),
        ),
    ],
    10,
)
MOCK_EMBEDDINGS_BASIC = [
    Embedding(
        id="1",
        seq_num=0,
        text="word word1" * i,
        embedding=[0.01],
        document_id="123",
        owner_id="owner",
    )
    for i in range(1, 4)
]
MOCK_EMBEDDINGS_OVERFLOW = [
    Embedding(
        id="2",
        seq_num=1,
        text="word word1" * i,
        embedding=[0.01],
        document_id="123",
        owner_id="owner",
    )
    for i in range(1, 9)
]


@pytest.mark.parametrize(
    "mock_inferences,max_history,actual_length",
    [(BASIC_MOCK_INFERENCES, 50, 3), (BASIC_MOCK_OVERFLOW, 25, 3)],
)
@pytest.mark.unit_tests
def test_create_memory_context_base_case(mock_inferences, max_history, actual_length):
    # setup
    with patch(
        "repositories.inference_repository.InferenceRepository",
    ) as mock_inference_repo:
        mock_inference_repo.return_value.query_inferences.return_value = mock_inferences
        conversation_id = "test_conversation"
        file_ids = ["id1", "id2"]

        # test
        ArthurChat.MAX_HISTORY_CONTEXT = max_history
        arthur_chat = ArthurChat(
            mock_inference_repo.return_value,
            MagicMock(),
            conversation_id,
            file_ids,
        )

        # verify
        assert len(arthur_chat.previous_message_history) == actual_length

        # approx verify total token
        assert arthur_chat.total_token_count < ArthurChat.MAX_HISTORY_CONTEXT

    ArthurChat.MAX_HISTORY_CONTEXT = 1024


@pytest.mark.parametrize(
    "mock_inferences,max_history,actual_length",
    [(BASIC_MOCK_CURLY_BRACKETS, 50, 3)],
)
@pytest.mark.unit_tests
def test_create_memory_context_curly_brackets_case_sanitization(
    mock_inferences,
    max_history,
    actual_length,
):
    # setup
    with patch(
        "repositories.inference_repository.InferenceRepository",
    ) as mock_inference_repo:
        mock_inference_repo.return_value.query_inferences.return_value = mock_inferences
        conversation_id = "test_conversation"
        file_ids = ["id1", "id2"]

        # test
        ArthurChat.MAX_HISTORY_CONTEXT = max_history
        arthur_chat = ArthurChat(
            mock_inference_repo.return_value,
            MagicMock(),
            conversation_id,
            file_ids,
        )

        # single brackets should be changed to double brackets
        human_input = str(arthur_chat.previous_message_history[1])
        llm_response = str(arthur_chat.previous_message_history[2])

        assert "{{word1}}" in human_input
        assert "{{word2}}" in llm_response

        # existing double brackets should remain the same
        human_input_2 = str(arthur_chat.previous_message_history[3])
        llm_response_2 = str(arthur_chat.previous_message_history[4])

        assert "{{word3}}" in human_input_2
        assert "{{word4}}" in llm_response_2

    ArthurChat.MAX_HISTORY_CONTEXT = 1024


@pytest.mark.parametrize(
    "mock_embeddings,max_context,actual_length",
    [(MOCK_EMBEDDINGS_BASIC, 100, 4), (MOCK_EMBEDDINGS_OVERFLOW, 50, 3)],
)
@pytest.mark.unit_tests
def test_retrieve_augmented_context(mock_embeddings, max_context, actual_length):
    # setup
    with patch(
        "repositories.embedding_repository.EmbeddingRepository",
    ) as mock_embedding_repo:
        with patch(
            "repositories.inference_repository.InferenceRepository",
        ) as mock_inference_repo:
            mock_embedding_repo.return_value.get_embeddings.return_value = (
                mock_embeddings
            )

            mock_inference_repo.return_value.query_inferences.return_value = (
                BASIC_MOCK_INFERENCES
            )
            conversation_id = "test_conversation"
            file_ids = ["id1", "id2"]

            # test
            ArthurChat.MAX_CONTEXT_LIMIT = max_context
            arthur_chat = ArthurChat(
                mock_inference_repo.return_value,
                mock_embedding_repo.return_value,
                conversation_id,
                file_ids,
            )
            retrieval_info = arthur_chat.retrieve_augmented_context("test_query")

            # verify
            assert len(retrieval_info.messages) == actual_length

            # approx verify total token
            assert arthur_chat.total_token_count < ArthurChat.MAX_CONTEXT_LIMIT

    ArthurChat.MAX_CONTEXT_LIMIT = 4096  # Reset global variable to initial value
