from datetime import datetime
from typing import Optional
from uuid import UUID

from arthur_common.models.response_schemas import ExternalInference
from pydantic import BaseModel, Field


class DocumentStorageConfigurationResponse(BaseModel):
    storage_environment: Optional[str] = None
    bucket_name: Optional[str] = None
    container_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None


class ApplicationConfigurationResponse(BaseModel):
    chat_task_id: Optional[str] = None
    document_storage_configuration: Optional[DocumentStorageConfigurationResponse] = (
        None
    )
    max_llm_rules_per_task_count: int


class ConversationBaseResponse(BaseModel):
    id: str
    updated_at: datetime


class ConversationResponse(ConversationBaseResponse):
    inferences: list[ExternalInference]


class HealthResponse(BaseModel):
    message: str
    build_version: Optional[str] = None


class DatasetResponse(BaseModel):
    id: UUID = Field(description="ID of the dataset.")
    name: str = Field(
        description="Name of the dataset.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the dataset.",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Any metadata to include that describes additional information about the dataset.",
    )
    created_at: int = Field(
        description="Timestamp representing the time of dataset creation in unix milliseconds.",
    )
    updated_at: int = Field(
        description="Timestamp representing the time of the last dataset update in unix milliseconds.",
    )


class SearchDatasetsResponse(BaseModel):
    count: int = Field(
        description="The total number of datasets matching the parameters.",
    )
    datasets: list[DatasetResponse] = Field(
        description="List of datasets matching the search filters. Length is less than or equal to page_size parameter",
    )
