"""
Service for generating synthetic dataset rows using LLM.

This module provides the SyntheticDataService class which handles:
1. Initial synthetic data generation based on dataset configuration
2. Conversational refinement of generated data
"""

import uuid
from typing import Any, Dict, List, Optional, cast

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient, LLMModelResponse
from repositories.model_provider_repository import ModelProviderRepository
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
from services.synthetic_data_tracing_service import SyntheticDataTracingService


class SyntheticDataColumn(BaseModel):
    """A single column-value pair in a synthetic data row."""

    column_name: str = Field(description="Name of the column.")
    column_value: str = Field(description="Value for this column.")


class SyntheticDataRow(BaseModel):
    """A single row of synthetic data."""

    id: str = Field(description="Unique identifier for the row.")
    data: List[SyntheticDataColumn] = Field(
        description="List of column-value pairs in the row.",
    )


class SyntheticDataLLMOutput(BaseModel):
    """Schema for structured LLM output for synthetic data generation."""

    rows: List[SyntheticDataRow] = Field(
        description="List of generated data rows.",
    )
    message: str = Field(
        description="Explanation of what was done",
    )


class SyntheticDataService:
    """Service for generating and refining synthetic dataset rows."""

    def __init__(
        self,
        model_provider_repo: ModelProviderRepository,
        db_session: Session,
    ):
        self.model_provider_repo = model_provider_repo
        self.tracing = SyntheticDataTracingService(db_session)

    def _get_llm_client(self, provider: ModelProvider) -> LLMClient:
        """Get configured LLM client from the model provider repository."""
        return self.model_provider_repo.get_model_provider_client(provider)

    @staticmethod
    def _extract_token_counts(
        response: LLMModelResponse,
    ) -> tuple[Optional[int], Optional[int], Optional[int]]:
        raw = response.response
        if raw is None or not hasattr(raw, "usage") or not raw.usage:
            return None, None, None
        usage = raw.usage
        return (
            getattr(usage, "prompt_tokens", None),
            getattr(usage, "completion_tokens", None),
            getattr(usage, "total_tokens", None),
        )

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
        existing_row_ids: set[str],
    ) -> tuple[List[SyntheticDataRowResponse], List[str], List[str], List[str]]:
        """
        Parse LLM output and determine which rows were added, modified, or removed.

        Returns:
            Tuple of (rows, rows_added, rows_modified, rows_removed)
        """
        rows = []
        rows_added = []
        rows_modified = []
        new_row_ids: set[str] = set()

        for row in llm_output.rows:
            new_row_ids.add(row.id)

            data = [
                DatasetVersionRowColumnItemResponse(
                    column_name=col.column_name,
                    column_value=col.column_value,
                )
                for col in row.data
            ]

            rows.append(SyntheticDataRowResponse(id=row.id, data=data))

            if row.id in existing_row_ids:
                rows_modified.append(row.id)
            else:
                rows_added.append(row.id)

        rows_removed = list(existing_row_ids - new_row_ids)

        return rows, rows_added, rows_modified, rows_removed

    def _build_config_kwargs(
        self,
        config: Optional[LLMRequestConfigSettings],
    ) -> Dict[str, Any]:
        """Build kwargs for LLM completion from config settings."""
        if not config:
            return {"temperature": 0.7, "drop_params": True}

        kwargs: Dict[str, Any] = {"drop_params": True}
        if config.temperature is not None:
            kwargs["temperature"] = config.temperature
        else:
            kwargs["temperature"] = 0.7

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
        session_id: str,
    ) -> SyntheticDataGenerationResponse:
        """
        Generate initial synthetic data based on the configuration.

        Args:
            request: The generation request with configuration
            existing_rows: Sample of existing dataset rows for reference
            column_names: List of column names in the dataset
            session_id: Identifier linking spans from the same SDG session

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
        messages: List[OpenAIMessage] = [
            OpenAIMessage(role=MessageRole.SYSTEM, content=system_prompt),
            OpenAIMessage(role=MessageRole.USER, content=user_prompt),
        ]

        # Build config kwargs
        config_kwargs = self._build_config_kwargs(request.config)

        agent_span = self.tracing.start_agent_span("initial_generation", session_id)
        self.tracing.set_agent_input(
            agent_span,
            {
                "dataset_purpose": request.dataset_purpose,
                "num_rows": request.num_rows,
                "column_names": column_names,
            },
        )
        llm_span = self.tracing.start_llm_span(
            agent_span,
            request.model_name,
            (
                request.model_provider.value
                if hasattr(request.model_provider, "value")
                else str(request.model_provider)
            ),
        )
        self.tracing.set_llm_input_messages(llm_span, messages)

        try:
            response = client.completion(
                model=request.model_name,
                messages=[m.model_dump(exclude_none=True) for m in messages],
                response_format=SyntheticDataLLMOutput,
                **config_kwargs,
            )
        except Exception as e:
            self.tracing.end_span_with_error(llm_span, str(e))
            self.tracing.end_span_with_error(agent_span, str(e))
            self.tracing.flush()
            raise

        llm_output = cast(SyntheticDataLLMOutput, response.structured_output_response)
        input_tokens, output_tokens, total_tokens = self._extract_token_counts(response)
        self.tracing.set_llm_response(
            llm_span,
            content=llm_output.model_dump_json(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        self.tracing.end_span(llm_span)

        # Parse the response
        rows, rows_added, rows_modified, rows_removed = self._parse_llm_response(
            llm_output,
            existing_row_ids=set(),  # No existing rows for initial generation
        )

        # Create assistant message
        assistant_message = OpenAIMessage(
            role=MessageRole.AI,
            content=llm_output.message,
        )

        self.tracing.set_agent_output(
            agent_span,
            {
                "message": llm_output.message,
                "rows_added": rows_added,
                "rows_modified": rows_modified,
                "rows_removed": rows_removed,
            },
        )
        self.tracing.end_span(agent_span)
        self.tracing.flush()

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
        session_id: str,
    ) -> SyntheticDataGenerationResponse:
        """
        Continue the synthetic data generation conversation.

        Args:
            request: The conversation request with user message and current state
            existing_rows: Sample of existing dataset rows for reference
            column_names: List of column names in the dataset
            session_id: Identifier linking spans from the same SDG session

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
        messages: List[OpenAIMessage] = [
            OpenAIMessage(role=MessageRole.SYSTEM, content=system_prompt),
            *request.conversation_history,
            OpenAIMessage(role=MessageRole.USER, content=user_prompt),
        ]

        # Build config kwargs
        config_kwargs = self._build_config_kwargs(request.config)

        agent_span = self.tracing.start_agent_span("conversation", session_id)
        self.tracing.set_agent_input(
            agent_span,
            {
                "dataset_purpose": request.dataset_purpose,
                "user_message": request.message,
                "current_row_count": len(current_rows_internal),
                "column_names": column_names,
            },
        )
        llm_span = self.tracing.start_llm_span(
            agent_span,
            request.model_name,
            (
                request.model_provider.value
                if hasattr(request.model_provider, "value")
                else str(request.model_provider)
            ),
        )
        self.tracing.set_llm_input_messages(llm_span, messages)

        try:
            response = client.completion(
                model=request.model_name,
                messages=[m.model_dump(exclude_none=True) for m in messages],
                response_format=SyntheticDataLLMOutput,
                **config_kwargs,
            )
        except Exception as e:
            self.tracing.end_span_with_error(llm_span, str(e))
            self.tracing.end_span_with_error(agent_span, str(e))
            self.tracing.flush()
            raise

        llm_output = cast(SyntheticDataLLMOutput, response.structured_output_response)
        input_tokens, output_tokens, total_tokens = self._extract_token_counts(response)
        self.tracing.set_llm_response(
            llm_span,
            content=llm_output.model_dump_json(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        self.tracing.end_span(llm_span)

        # Parse the response
        rows, rows_added, rows_modified, rows_removed = self._parse_llm_response(
            llm_output,
            existing_row_ids=current_row_ids,
        )

        # Create assistant message
        assistant_message = OpenAIMessage(
            role=MessageRole.AI,
            content=llm_output.message,
        )

        self.tracing.set_agent_output(
            agent_span,
            {
                "message": llm_output.message,
                "rows_added": rows_added,
                "rows_modified": rows_modified,
                "rows_removed": rows_removed,
            },
        )
        self.tracing.end_span(agent_span)
        self.tracing.flush()

        return SyntheticDataGenerationResponse(
            rows=rows,
            assistant_message=assistant_message,
            rows_added=rows_added,
            rows_modified=rows_modified,
            rows_removed=rows_removed,
        )
