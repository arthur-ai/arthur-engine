from typing import List

from pydantic import BaseModel


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
