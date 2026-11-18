import json
from typing import Any, Dict, List, Optional

from arthur_common.models.llm_model_providers import ModelProvider, OpenAIMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatbotConfigResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    model_provider: Optional[ModelProvider] = Field(
        default=None,
        description="Provider the chatbot calls. Null when it uses the default model provider and none is set.",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Model the chatbot calls. Null when it uses the default model provider and none is set.",
    )
    uses_default_model: bool = Field(
        default=False,
        description="True when the chatbot follows the instance's default model provider instead of a model picked for it.",
    )
    blacklist_endpoints: List[str] = []
    available_endpoints: List[str] = []


class ChatbotConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    model_provider: Optional[ModelProvider] = None
    model_name: Optional[str] = None
    blacklist_endpoints: Optional[List[str]] = None


class SearchArthurApiArgs(BaseModel):
    query: str = ""


class WikipediaSearchArgs(BaseModel):
    query: str = ""


class WikipediaFetchArgs(BaseModel):
    title: str = ""


class WikipediaSearchResult(BaseModel):
    titles: List[str] = Field(default_factory=list)


class WikipediaArticle(BaseModel):
    title: str
    extract: str
    url: str = ""


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
    history: List[OpenAIMessage]
    session_id: Optional[str] = None


class ChatbotResponse(BaseModel):
    message: str
    api_calls_made: List[ApiCallSummary]
