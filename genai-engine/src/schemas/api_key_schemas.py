from typing import Optional
from uuid import UUID

from arthur_common.models.request_schemas import (
    NewApiKeyRequest as BaseNewApiKeyRequest,
)
from arthur_common.models.response_schemas import ApiKeyResponse as BaseApiKeyResponse
from pydantic import Field


class NewApiKeyRequest(BaseNewApiKeyRequest):
    task_id: Optional[UUID] = Field(
        default=None,
        description="Scope the key to this one task. A task-scoped key can only reach "
        "routes that check the task, only for this task, and its traces always land "
        "in this task. Omit for a key that is not limited to one task.",
    )


class ApiKeyResponse(BaseApiKeyResponse):
    task_id: Optional[str] = Field(
        default=None,
        description="The task this key is scoped to. None for keys not limited to one task.",
    )
