from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, model_validator

from schemas.enums import (
    DocumentStorageEnvironment,
    ModelProvider,
)


class DocumentStorageConfigurationUpdateRequest(BaseModel):
    environment: DocumentStorageEnvironment
    connection_string: Optional[str] = None
    container_name: Optional[str] = None
    bucket_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None

    @model_validator(mode="before")
    def check_azure_or_aws_complete_config(cls, values):
        if values.get("environment") == "azure":
            if (values.get("connection_string") is None) or (
                values.get("container_name") is None
            ):
                raise ValueError(
                    "Both connection string and container name must be supplied for Azure document configuration",
                )
        elif values.get("environment") == "aws":
            if values.get("bucket_name") is None:
                raise ValueError(
                    "Bucket name must be supplied for AWS document configuration",
                )
            if values.get("assumable_role_arn") is None:
                raise ValueError(
                    "Role ARN must be supplied for AWS document configuration",
                )
        return values


class ApplicationConfigurationUpdateRequest(BaseModel):
    chat_task_id: Optional[str] = None
    document_storage_configuration: Optional[
        DocumentStorageConfigurationUpdateRequest
    ] = None
    max_llm_rules_per_task_count: Optional[int] = None


class NewDatasetRequest(BaseModel):
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


class DatasetUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        description="Name of the dataset.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the dataset.",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Any metadata to include that describes additional information about the dataset.",
        examples=[{"created_by": "John Doe"}],
    )


class NewDatasetVersionRowColumnItemRequest(BaseModel):
    column_name: str = Field(description="Name of column.")
    column_value: str = Field(description="Value of column for the row.")


class NewDatasetVersionRowRequest(BaseModel):
    data: List[NewDatasetVersionRowColumnItemRequest] = Field(
        description="List of column-value pairs in the new dataset row.",
    )


class NewDatasetVersionUpdateRowRequest(BaseModel):
    id: UUID = Field(description="UUID of row to be updated.")
    data: List[NewDatasetVersionRowColumnItemRequest] = Field(
        description="List of column-value pairs in the updated row.",
    )


class NewDatasetVersionRequest(BaseModel):
    rows_to_add: list[NewDatasetVersionRowRequest] = Field(
        description="List of rows to be added to the new dataset version.",
    )
    rows_to_delete: list[UUID] = Field(
        description="List of IDs of rows to be deleted from the new dataset version.",
    )
    rows_to_update: list[NewDatasetVersionUpdateRowRequest] = Field(
        description="List of IDs of rows to be updated in the new dataset version with their new values. "
        "Should include the value in the row for every column in the dataset, not just the updated column values.",
    )


class PutModelProviderCredentials(BaseModel):
    api_key: SecretStr = Field(description="The API key for the provider.")


class AgenticPromptFilterRequest(BaseModel):
    """Request schema for filtering agentic prompts with comprehensive filtering options."""

    # Optional filters
    prompt_names: Optional[list[str]] = Field(
        None,
        description="Prompt names to filter on. If provided, only prompts with these names will be returned.",
    )
    model_provider: Optional[ModelProvider] = Field(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    )
    model_name: Optional[str] = Field(
        None,
        description="Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').",
    )
    start_time: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    end_time: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    exclude_deleted: Optional[bool] = Field(
        False,
        description="Whether to exclude deleted prompt versions from the results. Default is False.",
    )
    min_version: Optional[int] = Field(
        None,
        ge=1,
        description="Minimum version number to filter on (inclusive).",
    )
    max_version: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum version number to filter on (inclusive).",
    )
