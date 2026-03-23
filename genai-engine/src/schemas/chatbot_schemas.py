import json
from typing import Any, Dict, List, Optional

from arthur_common.models.llm_model_providers import ModelProvider
from pydantic import BaseModel, ConfigDict, field_validator


class ChatbotConfigResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    model_provider: ModelProvider
    model_name: str
    blacklist_endpoints: List[str] = []
    available_endpoints: List[str] = []


class ChatbotConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    model_provider: Optional[ModelProvider] = None
    model_name: Optional[str] = None
    blacklist_endpoints: Optional[List[str]] = None


class SearchArthurApiArgs(BaseModel):
    query: str = ""


class CallArthurApiArgs(BaseModel):
    method: str = "GET"
    path: str = "/"
    query_params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None

    @field_validator("query_params", "body", mode="before")
    @classmethod
    def parse_stringified_json(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v


class ApiCallSummary(BaseModel):
    method: str
    path: str
    status_code: int


class ChatbotRequest(BaseModel):
    message: str
    conversation_id: str


class ChatbotResponse(BaseModel):
    message: str
    conversation_id: str
    api_calls_made: List[ApiCallSummary]
