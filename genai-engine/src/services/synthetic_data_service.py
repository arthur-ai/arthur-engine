"""
Service for generating synthetic dataset rows using LLM.

This module provides the SyntheticDataService class which handles:
1. Initial synthetic data generation based on dataset configuration
2. Conversational refinement of generated data
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from clients.llm.llm_client import LLMClient
from repositories.model_provider_repository import ModelProviderRepository
from schemas.enums import ModelProvider
from schemas.llm_schemas import OpenAIMessage
from schemas.request_schemas import (
    LLMRequestConfigSettings,
    SyntheticDataColumnDescription,
    SyntheticDataConversationRequest,
    SyntheticDataGenerationRequest,
)
from schemas.response_schemas import (
    DatasetVersionRowColumnItemResponse,
    SyntheticDataGenerationResponse,
    SyntheticDataRowResponse,
)
from services.synthetic_data_prompts import (
    build_conversation_prompt,
    build_initial_generation_prompt,
    build_system_prompt,
)


class SyntheticDataLLMOutput(BaseModel):
    """Schema for structured LLM output for synthetic data generation.

    Uses a JSON string for rows to avoid OpenAI structured output limitations
    with nested complex types.
    """

    rows_json: str = Field(
        description=(
            "JSON array of row objects. Each row has 'id' (string) and 'data' "
            "(array of {column_name, column_value} objects). "
            'Example: [{"id": "1", "data": [{"column_name": "col1", "column_value": "val1"}]}]'
        ),
    )
    message: str = Field(
        description="Explanation of what was done",
    )


class SyntheticDataService:
    """Service for generating and refining synthetic dataset rows."""

    def __init__(self, model_provider_repo: ModelProviderRepository):
        self.model_provider_repo = model_provider_repo

    def _get_llm_client(self, provider: ModelProvider) -> LLMClient:
        """Get configured LLM client from the model provider repository."""
        return self.model_provider_repo.get_model_provider_client(provider)

    def _convert_column_descriptions_to_dicts(
        self,
        column_descriptions: List[SyntheticDataColumnDescription],
    ) -> List[Dict[str, str]]:
        """Convert column description objects to dictionaries."""
        return [
            {
                "column_name": col.column_name,
                "description": col.description,
            }
            for col in column_descriptions
        ]

    def _convert_existing_rows_to_dicts(
        self,
        existing_rows: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Convert existing dataset rows to simple dictionaries."""
        result = []
        for row in existing_rows:
            row_dict = {}
            data = row.get("data", [])
            for item in data:
                col_name = item.get("column_name", "")
                col_value = item.get("column_value", "")
                row_dict[col_name] = col_value
            result.append(row_dict)
        return result

    def _parse_llm_response(
        self,
        llm_output: SyntheticDataLLMOutput,
        existing_row_ids: set,
    ) -> tuple[List[SyntheticDataRowResponse], List[str], List[str], List[str]]:
        """
        Parse LLM output and determine which rows were added, modified, or removed.

        Returns:
            Tuple of (rows, rows_added, rows_modified, rows_removed)
        """
        rows = []
        rows_added = []
        rows_modified = []

        new_row_ids = set()

        # Parse the JSON string to get rows
        try:
            parsed_rows = json.loads(llm_output.rows_json)
        except json.JSONDecodeError:
            parsed_rows = []

        for row in parsed_rows:
            row_id = row.get("id", str(uuid.uuid4()))
            new_row_ids.add(row_id)

            # Convert data to response format
            row_data = row.get("data", [])
            data = [
                DatasetVersionRowColumnItemResponse(
                    column_name=item.get("column_name", ""),
                    column_value=item.get("column_value", ""),
                )
                for item in row_data
            ]

            rows.append(SyntheticDataRowResponse(id=row_id, data=data))

            # Track if this is a new or modified row
            if row_id in existing_row_ids:
                rows_modified.append(row_id)
            else:
                rows_added.append(row_id)

        # Determine removed rows (IDs that were in existing but not in new)
        rows_removed = list(existing_row_ids - new_row_ids)

        return rows, rows_added, rows_modified, rows_removed

    def _build_config_kwargs(
        self,
        config: Optional[LLMRequestConfigSettings],
    ) -> Dict[str, Any]:
        """Build kwargs for LLM completion from config settings."""
        if not config:
            return {"temperature": 0.7}  # Default temperature for creative generation

        kwargs = {}
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature
        else:
            kwargs["temperature"] = 0.7  # Default for creative generation

        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        if config.top_p is not None:
            kwargs["top_p"] = config.top_p
        if config.frequency_penalty is not None:
            kwargs["frequency_penalty"] = config.frequency_penalty
        if config.presence_penalty is not None:
            kwargs["presence_penalty"] = config.presence_penalty
        if config.seed is not None:
            kwargs["seed"] = config.seed

        return kwargs

    def generate_initial(
        self,
        request: SyntheticDataGenerationRequest,
        existing_rows: List[Dict[str, Any]],
        column_names: List[str],
    ) -> SyntheticDataGenerationResponse:
        """
        Generate initial synthetic data based on the configuration.

        Args:
            request: The generation request with configuration
            existing_rows: Sample of existing dataset rows for reference
            column_names: List of column names in the dataset

        Returns:
            SyntheticDataGenerationResponse with generated rows
        """
        client = self._get_llm_client(request.model_provider)

        # Convert column descriptions to dict format
        column_desc_dicts = self._convert_column_descriptions_to_dicts(
            request.column_descriptions,
        )

        # Convert existing rows to simple dict format
        existing_rows_dicts = self._convert_existing_rows_to_dicts(existing_rows)

        # Build prompts
        system_prompt = build_system_prompt(
            dataset_purpose=request.dataset_purpose,
            column_descriptions=column_desc_dicts,
            existing_rows=existing_rows_dicts,
            column_names=column_names,
        )

        user_prompt = build_initial_generation_prompt(num_rows=request.num_rows)

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Build config kwargs
        config_kwargs = self._build_config_kwargs(request.config)

        # Call LLM with JSON mode (compatible with all models)
        response = client.completion(
            model=request.model_name,
            messages=messages,
            response_format={"type": "json_object"},
            **config_kwargs,
        )

        # Parse JSON response manually
        content = response.response.choices[0].message.get("content", "{}")
        try:
            parsed_json = json.loads(content)
            llm_output = SyntheticDataLLMOutput(
                rows_json=json.dumps(parsed_json.get("rows", [])),
                message=parsed_json.get("message", "Generated data successfully."),
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM response was not valid JSON: {e}") from e

        # Parse the response
        rows, rows_added, rows_modified, rows_removed = self._parse_llm_response(
            llm_output,
            existing_row_ids=set(),  # No existing rows for initial generation
        )

        # Create assistant message
        assistant_message = OpenAIMessage(
            role="assistant",
            content=llm_output.message,
        )

        return SyntheticDataGenerationResponse(
            rows=rows,
            assistant_message=assistant_message,
            rows_added=rows_added,
            rows_modified=rows_modified,
            rows_removed=rows_removed,
        )

    def continue_conversation(
        self,
        request: SyntheticDataConversationRequest,
        existing_rows: List[Dict[str, Any]],
        column_names: List[str],
    ) -> SyntheticDataGenerationResponse:
        """
        Continue the synthetic data generation conversation.

        Args:
            request: The conversation request with user message and current state
            existing_rows: Sample of existing dataset rows for reference
            column_names: List of column names in the dataset

        Returns:
            SyntheticDataGenerationResponse with updated rows
        """
        client = self._get_llm_client(request.model_provider)

        # Convert column descriptions to dict format
        column_desc_dicts = self._convert_column_descriptions_to_dicts(
            request.column_descriptions,
        )

        # Convert existing rows to simple dict format
        existing_rows_dicts = self._convert_existing_rows_to_dicts(existing_rows)

        # Build system prompt (same as initial)
        system_prompt = build_system_prompt(
            dataset_purpose=request.dataset_purpose,
            column_descriptions=column_desc_dicts,
            existing_rows=existing_rows_dicts,
            column_names=column_names,
        )

        # Convert current rows to internal format for the prompt
        current_rows_internal = []
        current_row_ids = set()
        for row in request.current_rows:
            # Use the provided row ID if available, otherwise generate a new one
            row_id = row.id if row.id is not None else str(uuid.uuid4())
            # Handle NewDatasetVersionRowRequest format
            row_data = []
            if hasattr(row, "data"):
                for item in row.data:
                    if hasattr(item, "column_name") and hasattr(item, "column_value"):
                        row_data.append(
                            {
                                "column_name": item.column_name,
                                "column_value": item.column_value,
                            }
                        )
            current_rows_internal.append({"id": row_id, "data": row_data})
            current_row_ids.add(row_id)

        # Build conversation user prompt
        user_prompt = build_conversation_prompt(
            user_message=request.message,
            current_rows=current_rows_internal,
            column_names=column_names,
        )

        # Build messages including conversation history
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in request.conversation_history:
            messages.append(
                {
                    "role": msg.role,
                    "content": (
                        msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content)
                    ),
                }
            )

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})

        # Build config kwargs
        config_kwargs = self._build_config_kwargs(request.config)

        # Call LLM with JSON mode (compatible with all models)
        response = client.completion(
            model=request.model_name,
            messages=messages,
            response_format={"type": "json_object"},
            **config_kwargs,
        )

        # Parse JSON response manually
        content = response.response.choices[0].message.get("content", "{}")
        try:
            parsed_json = json.loads(content)
            llm_output = SyntheticDataLLMOutput(
                rows_json=json.dumps(parsed_json.get("rows", [])),
                message=parsed_json.get("message", "Updated data successfully."),
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM response was not valid JSON: {e}") from e

        # Parse the response
        rows, rows_added, rows_modified, rows_removed = self._parse_llm_response(
            llm_output,
            existing_row_ids=current_row_ids,
        )

        # Create assistant message
        assistant_message = OpenAIMessage(
            role="assistant",
            content=llm_output.message,
        )

        return SyntheticDataGenerationResponse(
            rows=rows,
            assistant_message=assistant_message,
            rows_added=rows_added,
            rows_modified=rows_modified,
            rows_removed=rows_removed,
        )
