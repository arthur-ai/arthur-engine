from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SearchArthurApiArgs(BaseModel):
    query: str = ""


class CallArthurApiArgs(BaseModel):
    method: str = "GET"
    path: str = "/"
    query_params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None


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
