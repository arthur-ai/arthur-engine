import json
from typing import Any, Dict, List, Optional

from arthur_common.models.llm_model_providers import ModelProvider, OpenAIMessage
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    use_default_model: Optional[bool] = Field(
        default=None,
        description=(
            "True moves the chatbot back to the instance's default model provider. "
            "Can't be combined with model_provider or model_name."
        ),
    )
    blacklist_endpoints: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_one_model_choice(self) -> "ChatbotConfigUpdateRequest":
        if self.use_default_model and (self.model_provider or self.model_name):
            raise ValueError(
                "Set either use_default_model or model_provider and model_name, not both.",
            )
        return self


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
