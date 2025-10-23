from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Query

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
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


class BasePromptFilterRequest(BaseModel, ABC):
    """Abstract Pydantic base class enforcing apply_filters_to_query implementation."""

    @abstractmethod
    def apply_filters_to_query(self, query: Query) -> Query:
        """Apply filters to a SQLAlchemy query."""


class PromptsGetVersionsFilterRequest(BasePromptFilterRequest):
    """Request schema for filtering agentic prompts with comprehensive filtering options."""

    # Optional filters
    model_provider: Optional[ModelProvider] = Field(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    )
    model_name: Optional[str] = Field(
        None,
        description="Filter by model name using partial matching (e.g., 'gpt-4', 'claude'). Supports SQL LIKE pattern matching with % wildcards.",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
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

    def apply_filters_to_query(
        self,
        query: Query,
    ) -> Query:
        """
        Apply filters to a query based on the filter request.

        Parameters:
            query: Query - the SQLAlchemy query to filter

        Returns:
            Query - the query with filters applied
        """
        # Filter by model provider
        if self.model_provider:
            query = query.filter(
                DatabaseAgenticPrompt.model_provider == self.model_provider,
            )

        # Filter by model name using LIKE for partial matching
        if self.model_name:
            query = query.filter(
                DatabaseAgenticPrompt.model_name.like(f"%{self.model_name}%"),
            )

        # Filter by start time (inclusive)
        if self.created_after:
            query = query.filter(
                DatabaseAgenticPrompt.created_at >= self.created_after,
            )

        # Filter by end time (exclusive)
        if self.created_before:
            query = query.filter(
                DatabaseAgenticPrompt.created_at < self.created_before,
            )

        # Filter by deleted status
        if self.exclude_deleted == True:
            query = query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))

        # Filter by min version
        if self.min_version is not None:
            query = query.filter(
                DatabaseAgenticPrompt.version >= self.min_version,
            )

        # Filter by max version
        if self.max_version is not None:
            query = query.filter(
                DatabaseAgenticPrompt.version <= self.max_version,
            )

        return query


class PromptsGetAllFilterRequest(BasePromptFilterRequest):
    """Request schema for filtering agentic prompts with comprehensive filtering options."""

    # Optional filters
    prompt_names: Optional[list[str]] = Field(
        None,
        description="Prompt names to filter on using partial matching. If provided, prompts matching any of these name patterns will be returned. Supports SQL LIKE pattern matching with % wildcards.",
    )
    model_provider: Optional[ModelProvider] = Field(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    )
    model_name: Optional[str] = Field(
        None,
        description="Filter by model name using partial matching (e.g., 'gpt-4', 'claude'). Supports SQL LIKE pattern matching with % wildcards.",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )

    def apply_filters_to_query(
        self,
        query: Query,
    ) -> Query:
        """
        Apply filters to a query based on the filter request.

        Parameters:
            query: Query - the SQLAlchemy query to filter

        Returns:
            Query - the query with filters applied
        """
        # Filter by prompt names using LIKE for partial matching
        if self.prompt_names:
            name_conditions = [
                DatabaseAgenticPrompt.name.like(f"%{name}%")
                for name in self.prompt_names
            ]
            query = query.filter(or_(*name_conditions))

        # Filter by model provider
        if self.model_provider:
            query = query.filter(
                DatabaseAgenticPrompt.model_provider == self.model_provider,
            )

        # Filter by model name using LIKE for partial matching
        if self.model_name:
            query = query.filter(
                DatabaseAgenticPrompt.model_name.like(f"%{self.model_name}%"),
            )

        # Filter by start time (inclusive)
        if self.created_after:
            query = query.filter(
                DatabaseAgenticPrompt.created_at >= self.created_after,
            )

        # Filter by end time (exclusive)
        if self.created_before:
            query = query.filter(
                DatabaseAgenticPrompt.created_at < self.created_before,
            )

        return query
