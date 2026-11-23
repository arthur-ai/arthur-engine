from unittest.mock import patch
from uuid import uuid4

import pytest
from chat.embedding import EmbeddingModel
from repositories.embedding_repository import EmbeddingRepository
from schemas.internal_schemas import Embedding
from tests.clients.base_test_client import GenaiEngineTestClientBase


def generate_embeddings():
    return [
        Embedding(
            id="1",
            document_id="1",
            text="word word",
            seq_num=1,
            embedding=[0.0, 0.0, 0.0],
            owner_id="1",
        ),
    ] * 8


@patch.object(EmbeddingModel, "__init__", lambda *args: None)
@patch.object(EmbeddingModel, "embed_query", lambda *args: [1.0] * 1536)
@patch.object(EmbeddingRepository, "get_embeddings", return_value=generate_embeddings())
@patch("scorer.llm_client.LLMExecutor.execute")
@pytest.mark.unit_tests
def test_chat(execute, emb, client: GenaiEngineTestClientBase, clean_inference_tables):
    execute.return_value = ("good! how are you", None)

    # create task
    status_code, task_response = client.create_task("ArthurChat")
    assert status_code == 200
    new_config = {"chat_task_id": task_response.id}
    resp = client.update_configs(
        new_config,
        headers={"Authorization": "Bearer admin_0"},
    )

    # test for user with no documents
    user_prompt = "hello"
    conversation_id = "1"
    file_ids = ["id1", "id2"]
    status_code, chat_response = client.send_chat(
        user_prompt,
        conversation_id,
        file_ids,
    )
    assert status_code == 200
    assert chat_response.llm_response == "good! how are you"
    assert len(chat_response.retrieved_context) == 8


@pytest.mark.unit_tests
def test_context_returns_404(client: GenaiEngineTestClientBase, clean_inference_tables):
    not_existing_document_id = uuid4()
    status_code, _ = client.get_inference_document_context(not_existing_document_id)
    assert status_code == 404


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "page, size, expected_page, expected_size, expected_total, expected_items_len, create_conversation",
    [
        (1, 50, 1, 50, 1, 1, {}),
        (2, 50, 2, 50, 1, 0, {}),
    ],
    indirect=["create_conversation"],
)
def test_get_conversations(
    page: int,
    size: int,
    expected_page: int,
    expected_size: int,
    expected_total: int,
    expected_items_len: int,
    create_conversation,
    client: GenaiEngineTestClientBase,
):
    status_code, result = client.get_conversations(page=page, size=size)
    assert status_code == 200
    assert result.get("page") == expected_page
    assert result.get("size") == expected_size
    assert result.get("total") == expected_total
    assert len(result.get("items", [])) == expected_items_len


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "create_conversation",
    [{"number_of_messages": 2, "number_of_conversations": 2}],
    indirect=["create_conversation"],
)
def test_get_two_conversations(create_conversation, client: GenaiEngineTestClientBase):
    status_code, result = client.get_conversations()
    assert status_code == 200
    assert result.get("total") == 2
    assert len(result.get("items", [])) == 2


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "user_role",
    [
        ("genai_engine_user_0"),
    ],
)
def test_chat_not_enough_privilege(
    user_role: str,
    changed_user_client: GenaiEngineTestClientBase,
):
    client = changed_user_client
    user_prompt = "hello"
    conversation_id = "1"
    file_ids = ["id1", "id2"]
    status_code, chat_response = client.send_chat(
        user_prompt,
        conversation_id,
        file_ids,
    )
    assert status_code == 403
    assert chat_response is None
