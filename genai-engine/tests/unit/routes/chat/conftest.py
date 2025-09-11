from typing import Generator

import pytest
from repositories.inference_repository import InferenceRepository
from arthur_common.models.response_schemas import ConversationBaseResponse
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.fixture
def clean_inference_tables(user_id="00000000-1111-2222-3333-44444444"):
    db_session = override_get_db_session()
    inference_repository = InferenceRepository(
        db_session=db_session,
    )
    conversations: list[ConversationBaseResponse] = (
        inference_repository.get_all_user_conversations(user_id=user_id).items
    )
    inferences_ids = []
    for conversation in conversations:
        for inference in inference_repository.get_conversation_by_id(
            conversation.id,
            user_id,
        ).inferences:
            inferences_ids.append(inference.id)
    for inference in inferences_ids:
        inference_repository.delete_inference(inference_id=inference)

    yield


@pytest.fixture
def create_conversation(request):
    number_of_messages = request.param.get("number_of_messages", 1)
    number_of_conversations = request.param.get("number_of_conversations", 1)
    db_session = override_get_db_session()
    inferences_id: list[str] = []

    inference_repository = InferenceRepository(
        db_session=db_session,
    )
    for conversation_number in range(number_of_conversations):
        conversation_id = f"dummy_conversation_id_{conversation_number}"
        for message_number in range(number_of_messages):
            prompt = inference_repository.save_prompt(
                prompt=f"Is this the real life number {message_number}?",
                prompt_rule_results=[],
                conversation_id=conversation_id,
                user_id="00000000-1111-2222-3333-44444444",
            )
            inferences_id.append(prompt.inference_id)
            inference_repository.save_response(
                inference_id=prompt.inference_id,
                response=f"it's just fantasy number: {message_number}",
                response_context="",
                response_rule_results=[],
            )
    db_session.flush()

    yield

    for inference_id in inferences_id:
        inference_repository.delete_inference(inference_id=inference_id)


@pytest.fixture
def get_client_with_chat_task_created(
    client: GenaiEngineTestClientBase,
) -> Generator[GenaiEngineTestClientBase, None, None]:
    _, task_response = client.create_task("ArthurChat")
    new_config = {"chat_task_id": task_response.id}
    client.update_configs(
        new_config,
        headers=client.authorized_org_admin_api_key_headers,
    )

    yield client

    client.delete_task(task_response.id)
