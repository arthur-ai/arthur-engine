from __future__ import annotations

from typing import Optional

from arthur_common.models.enums import (
    PaginationSortMethod,
    UserPermissionAction,
    UserPermissionResource,
)
from pydantic import BaseModel


class PaginationParameters(BaseModel):
    sort: Optional[PaginationSortMethod] = PaginationSortMethod.DESCENDING
    page_size: int = 10
    page: int = 0

    def calculate_total_pages(self, total_items_count: int) -> int:
        return total_items_count // self.page_size + 1


class LLMTokenConsumption(BaseModel):
    prompt_tokens: int
    completion_tokens: int

    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    def add(self, token_consumption: LLMTokenConsumption):
        self.prompt_tokens += token_consumption.prompt_tokens
        self.completion_tokens += token_consumption.completion_tokens
        return self


class AuthUserRole(BaseModel):
    id: str | None = None
    name: str
    description: str
    composite: bool


class UserPermission(BaseModel):
    action: UserPermissionAction
    resource: UserPermissionResource

    def __hash__(self):
        return hash((self.action, self.resource))

    def __eq__(self, other):
        return isinstance(other, UserPermission) and self.__hash__() == other.__hash__()
