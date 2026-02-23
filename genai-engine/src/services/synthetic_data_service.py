"""
Service for generating synthetic dataset rows using LLM.

This module provides the SyntheticDataService class which handles:
1. Initial synthetic data generation based on dataset configuration
2. Conversational refinement of generated data
"""

import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, cast

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from jinja2.sandbox import SandboxedEnvironment
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient, LLMModelResponse
from dependencies import get_db_session
from repositories.agentic_prompts_repository import AgenticPromptRepository
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
    CONVERSATION_USER_PROMPT_TEMPLATE,
    INITIAL_GENERATION_USER_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    format_column_definitions,
    format_current_rows_for_prompt,
    format_reference_examples,
)
from services.trace.trace_ingestion_service import TraceIngestionService
from utils.constants import (
    PRODUCTION_TAG,
    SYNTHETIC_DATA_CONVERSATION_USER_PROMPT_NAME,
    SYNTHETIC_DATA_INITIAL_USER_PROMPT_NAME,
    SYNTHETIC_DATA_SYSTEM_PROMPT_NAME,
    SYNTHETIC_DATASET_TASK_ID,
)

logger = logging.getLogger(__name__)


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
        self, model_provider_repo: ModelProviderRepository, db_session: Session
    ):
        self.model_provider_repo = model_provider_repo
        self.db_session = db_session
        self._jinja_env = SandboxedEnvironment(autoescape=False)
        self._system_prompt_template = self._load_prompt_template(
            SYNTHETIC_DATA_SYSTEM_PROMPT_NAME
        )
        self._initial_user_prompt_template = self._load_prompt_template(
            SYNTHETIC_DATA_INITIAL_USER_PROMPT_NAME
        )
        self._conversation_user_prompt_template = self._load_prompt_template(
            SYNTHETIC_DATA_CONVERSATION_USER_PROMPT_NAME
        )

    def _load_prompt_template(self, prompt_name: str) -> str:
        """Fetch the 'production' tagged prompt from the system task and return its content."""
        try:
            with self.db_session.no_autoflush:
                prompt_repo = AgenticPromptRepository(self.db_session)
                prompt = prompt_repo.get_llm_item_by_tag(
                    SYNTHETIC_DATASET_TASK_ID, prompt_name, PRODUCTION_TAG
                )
            return prompt.messages[0].content  # type: ignore[return-value]
        except Exception as e:
            logger.warning(
                f"Could not load prompt template '{prompt_name}' from DB, "
                f"falling back to built-in template: {e}"
            )
            fallbacks = {
                SYNTHETIC_DATA_SYSTEM_PROMPT_NAME: SYSTEM_PROMPT_TEMPLATE,
                SYNTHETIC_DATA_INITIAL_USER_PROMPT_NAME: INITIAL_GENERATION_USER_PROMPT_TEMPLATE,
                SYNTHETIC_DATA_CONVERSATION_USER_PROMPT_NAME: CONVERSATION_USER_PROMPT_TEMPLATE,
            }
            return fallbacks[prompt_name]

    def _get_llm_client(self, provider: ModelProvider) -> LLMClient:
        """Get configured LLM client from the model provider repository."""
        with self.db_session.no_autoflush:
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

    def _emit_trace(
        self,
        messages: List[Dict[str, Any]],
        response: LLMModelResponse,
        model_name: str,
        session_id: str,
        start_time_ns: int,
    ) -> None:
        """Build and ingest an OpenInference-formatted trace for this LLM interaction."""
        trace_id = os.urandom(16)
        span_id = os.urandom(8)
        now_ns = int(time.time() * 1e9)

        span = Span()
        span.trace_id = trace_id
        span.span_id = span_id
        span.name = "synthetic-data-generation"
        span.start_time_unix_nano = start_time_ns
        span.end_time_unix_nano = now_ns

        attrs: list[KeyValue] = [
            KeyValue(
                key="openinference.span.kind",
                value=AnyValue(string_value="LLM"),
            ),
            KeyValue(
                key="arthur_span_version",
                value=AnyValue(string_value="arthur_span_v1"),
            ),
            KeyValue(
                key="llm.model_name",
                value=AnyValue(string_value=model_name),
            ),
        ]

        # Input messages
        for i, msg in enumerate(messages):
            attrs.append(
                KeyValue(
                    key=f"llm.input_messages.{i}.message.role",
                    value=AnyValue(string_value=str(msg.get("role", ""))),
                )
            )
            attrs.append(
                KeyValue(
                    key=f"llm.input_messages.{i}.message.content",
                    value=AnyValue(string_value=str(msg.get("content", ""))),
                )
            )

        # Output message
        raw = response.response
        output_content = ""
        try:
            if hasattr(raw, "choices") and raw.choices:
                output_content = raw.choices[0].message.content or ""
        except Exception:
            pass
        attrs.append(
            KeyValue(
                key="llm.output_messages.0.message.role",
                value=AnyValue(string_value="assistant"),
            )
        )
        attrs.append(
            KeyValue(
                key="llm.output_messages.0.message.content",
                value=AnyValue(string_value=output_content),
            )
        )

        # Token counts
        try:
            if hasattr(raw, "usage") and raw.usage:
                attrs += [
                    KeyValue(
                        key="llm.token_count.prompt",
                        value=AnyValue(int_value=raw.usage.prompt_tokens or 0),
                    ),
                    KeyValue(
                        key="llm.token_count.completion",
                        value=AnyValue(int_value=raw.usage.completion_tokens or 0),
                    ),
                    KeyValue(
                        key="llm.token_count.total",
                        value=AnyValue(int_value=raw.usage.total_tokens or 0),
                    ),
                ]
        except Exception:
            pass

        attrs.append(
            KeyValue(
                key="session.id",
                value=AnyValue(string_value=session_id),
            )
        )

        # input.value / output.value — required for the UI Input/Output boxes
        user_messages = [m for m in messages if m.get("role") == "user"]
        input_value = user_messages[-1].get("content", "") if user_messages else ""
        attrs.append(
            KeyValue(
                key="input.value",
                value=AnyValue(string_value=str(input_value)),
            )
        )
        attrs.append(
            KeyValue(
                key="output.value",
                value=AnyValue(string_value=output_content),
            )
        )

        span.attributes.extend(attrs)

        scope_span = ScopeSpans()
        scope_span.scope.name = "synthetic-data-service"
        scope_span.spans.append(span)

        resource_span = ResourceSpans()
        resource_span.resource.attributes.extend(
            [
                KeyValue(
                    key="arthur.task",
                    value=AnyValue(string_value=SYNTHETIC_DATASET_TASK_ID),
                ),
                KeyValue(
                    key="service.name",
                    value=AnyValue(string_value="synthetic-dataset-generation"),
                ),
            ]
        )
        resource_span.scope_spans.append(scope_span)

        export_request = ExportTraceServiceRequest()
        export_request.resource_spans.append(resource_span)

        try:
            trace_db_gen = get_db_session()
            trace_db = next(trace_db_gen)
            try:
                svc = TraceIngestionService(trace_db)
                svc.process_trace_data(export_request.SerializeToString())
            finally:
                trace_db_gen.close()
        except Exception as e:
            logger.warning(f"Failed to emit synthetic data trace: {e}")

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

        # Build prompts using DB-loaded templates
        system_prompt = self._jinja_env.from_string(
            self._system_prompt_template
        ).render(
            dataset_purpose=request.dataset_purpose,
            column_definitions=format_column_definitions(column_desc_dicts),
            reference_examples=format_reference_examples(
                existing_rows_dicts, column_names
            ),
        )

        user_prompt = self._jinja_env.from_string(
            self._initial_user_prompt_template
        ).render(num_rows=request.num_rows)

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Build config kwargs
        config_kwargs = self._build_config_kwargs(request.config)

        # Call LLM with structured outputs
        llm_start_ns = int(time.time() * 1e9)
        response = client.completion(
            model=request.model_name,
            messages=messages,
            response_format=SyntheticDataLLMOutput,
            **config_kwargs,
        )

        llm_output = cast(SyntheticDataLLMOutput, response.structured_output_response)

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

        # Generate session ID for trace linkage
        session_id = str(uuid.uuid4())

        # Emit trace (best-effort)
        self._emit_trace(
            messages=messages,
            response=response,
            model_name=request.model_name,
            session_id=session_id,
            start_time_ns=llm_start_ns,
        )

        return SyntheticDataGenerationResponse(
            rows=rows,
            assistant_message=assistant_message,
            rows_added=rows_added,
            rows_modified=rows_modified,
            rows_removed=rows_removed,
            session_id=session_id,
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

        # Build system prompt using DB-loaded template
        system_prompt = self._jinja_env.from_string(
            self._system_prompt_template
        ).render(
            dataset_purpose=request.dataset_purpose,
            column_definitions=format_column_definitions(column_desc_dicts),
            reference_examples=format_reference_examples(
                existing_rows_dicts, column_names
            ),
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

        # Build conversation user prompt using DB-loaded template
        user_prompt = self._jinja_env.from_string(
            self._conversation_user_prompt_template
        ).render(
            current_rows=format_current_rows_for_prompt(
                current_rows_internal, column_names
            ),
            user_message=request.message,
        )

        # Build messages including conversation history
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in request.conversation_history:
            messages.append(
                {
                    "role": msg.role if isinstance(msg.role, str) else msg.role.value,
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

        # Call LLM with structured outputs
        llm_start_ns = int(time.time() * 1e9)
        response = client.completion(
            model=request.model_name,
            messages=messages,
            response_format=SyntheticDataLLMOutput,
            **config_kwargs,
        )

        llm_output = cast(SyntheticDataLLMOutput, response.structured_output_response)

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

        # Use existing session_id if provided, otherwise generate a new one
        session_id = request.session_id or str(uuid.uuid4())

        # Emit trace (best-effort)
        self._emit_trace(
            messages=messages,
            response=response,
            model_name=request.model_name,
            session_id=session_id,
            start_time_ns=llm_start_ns,
        )

        return SyntheticDataGenerationResponse(
            rows=rows,
            assistant_message=assistant_message,
            rows_added=rows_added,
            rows_modified=rows_modified,
            rows_removed=rows_removed,
            session_id=session_id,
        )
