from fastapi.testclient import TestClient

from .base_test_client import AUTHORIZED_CHAT_HEADERS, GenaiEngineTestClientBase, app


class GenaiEngineUnitTestClient(GenaiEngineTestClientBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def get_genai_engine_test_client(
    create_user_key: bool = True,
) -> GenaiEngineUnitTestClient:
    return GenaiEngineTestClientBase(
        client=TestClient(app),
        authorized_chat_headers=AUTHORIZED_CHAT_HEADERS,
        create_user_key=create_user_key,
        create_org_admin=True,
    )
