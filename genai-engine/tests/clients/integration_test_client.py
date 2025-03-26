import os

import httpx

from .base_test_client import GenaiEngineTestClientBase


class GenaiEngineIntegrationTestClient(GenaiEngineTestClientBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def get_genai_engine_test_client(
    create_user_key: bool = True,
) -> GenaiEngineIntegrationTestClient:
    return GenaiEngineTestClientBase(
        client=httpx.Client(base_url=os.environ["REMOTE_TEST_URL"], timeout=60),
        create_user_key=create_user_key,
        create_org_admin=True,
    )
