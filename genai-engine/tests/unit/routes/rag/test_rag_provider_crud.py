from uuid import uuid4

import pytest
from pydantic_core import Url

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_rag_provider_crud(client: GenaiEngineTestClientBase) -> None:
    """Test the basic happy path for rag provider CRUD operations: create, get, patch, delete."""
    # First create a task to associate the RAG provider with
    status_code, task = client.create_task(name="Test Task for RAG Provider")
    assert status_code == 200
    task_id = task.id

    # test rag provider creation
    rag_provider_name = "My Test RAG Provider"
    rag_provider_description = "Test RAG provider for CRUD operations"
    api_key = "test-api-key-123"
    host_url = "https://test-weaviate.example.com"

    # test provider creation for non-existing task
    status_code, _ = client.create_rag_provider(
        task_id=str(uuid4()),
        name=rag_provider_name,
        description=rag_provider_description,
        api_key=api_key,
        host_url=host_url,
    )
    assert status_code == 404

    status_code, created_rag_provider = client.create_rag_provider(
        task_id=task_id,
        name=rag_provider_name,
        description=rag_provider_description,
        api_key=api_key,
        host_url=host_url,
    )
    assert status_code == 200
    assert created_rag_provider.name == rag_provider_name
    assert created_rag_provider.description == rag_provider_description
    assert created_rag_provider.task_id == task_id
    assert created_rag_provider.id is not None
    assert created_rag_provider.authentication_config.authentication_method == "api_key"
    assert created_rag_provider.authentication_config.host_url == Url(host_url)

    # test rag provider fetch
    status_code, retrieved_rag_provider = client.get_rag_provider(
        created_rag_provider.id,
    )
    assert status_code == 200
    assert retrieved_rag_provider.id == created_rag_provider.id
    assert retrieved_rag_provider.name == rag_provider_name
    assert retrieved_rag_provider.description == rag_provider_description
    assert retrieved_rag_provider.task_id == task_id

    # test rag provider update
    updated_name = "Updated test RAG provider"
    updated_description = "Updated test RAG provider description"
    updated_api_key = "updated-api-key-456"
    updated_host_url = "https://updated-weaviate.example.com/"

    status_code, updated_rag_provider = client.update_rag_provider(
        provider_id=created_rag_provider.id,
        name=updated_name,
        description=updated_description,
        api_key=updated_api_key,
        host_url=updated_host_url,
    )
    assert status_code == 200
    assert updated_rag_provider.id == created_rag_provider.id
    assert updated_rag_provider.name == updated_name
    assert updated_rag_provider.description == updated_description
    assert updated_rag_provider.authentication_config.authentication_method == "api_key"
    assert updated_rag_provider.authentication_config.host_url == Url(updated_host_url)
    assert updated_rag_provider.updated_at > updated_rag_provider.created_at

    # validate updates persisted on fetch
    status_code, final_rag_provider = client.get_rag_provider(created_rag_provider.id)
    assert status_code == 200
    assert final_rag_provider.name == updated_name
    assert final_rag_provider.description == updated_description
    assert final_rag_provider.authentication_config.authentication_method == "api_key"
    assert final_rag_provider.authentication_config.host_url == Url(updated_host_url)

    # test search rag providers for task
    status_code, search_response = client.search_rag_providers(task_id=task_id)
    assert status_code == 200
    assert search_response.count == 1
    assert len(search_response.rag_provider_configurations) == 1
    assert search_response.rag_provider_configurations[0].id == created_rag_provider.id

    # delete rag provider
    status_code = client.delete_rag_provider(created_rag_provider.id)
    assert status_code == 204

    # fail to fetch rag provider because it was deleted
    status_code, _ = client.get_rag_provider(created_rag_provider.id)
    assert status_code == 404

    # fail to patch rag provider that doesn't exist
    status_code, _ = client.update_rag_provider(
        provider_id=created_rag_provider.id,
        name=updated_name,
        description=updated_description,
    )
    assert status_code == 404

    # fail to delete rag provider that doesn't exist
    status_code = client.delete_rag_provider(created_rag_provider.id)
    assert status_code == 404

    # Clean up the task
    status_code = client.delete_task(task_id)
    assert status_code == 204
