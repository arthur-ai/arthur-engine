"""
Service for converting GCP Cloud Trace spans to OpenInference format.

GCP Cloud Trace uses a simpler format with spans containing:
- spanId, name, startTime, endTime, parentSpanId
- labels (dict): Contains all attributes including GenAI semantic conventions

This service converts GCP labels to OpenInference attributes and prepares spans
for direct ingestion into the database.
"""

import logging
from datetime import datetime
from typing import Any

from benedict import benedict
from openinference.semconv.trace import SpanAttributes

logger = logging.getLogger(__name__)


class GcpConversionService:
    """Service for converting GCP Cloud Trace labels to OpenInference attributes"""

    def _determine_span_kind(self, attributes: dict[str, Any]) -> str:
        """
        Determine the OpenInference span kind based on label presence.

        Priority logic:
        - AGENT: Has gen_ai.agent.name
        - TOOL: Has gen_ai.tool.name
        - LLM: Has llm.model_name or gen_ai.request.model
        - UNKNOWN: Everything else

        Args:
            attributes: Dict of attributes (may include both GCP labels and OpenInference attributes)

        Returns:
            Span kind as string: "AGENT", "LLM", "TOOL", or "UNKNOWN"
        """
        if "gen_ai.agent.name" in attributes:
            return "AGENT"
        elif "gen_ai.tool.name" in attributes:
            return "TOOL"
        elif (
            SpanAttributes.LLM_MODEL_NAME in attributes
            or "gen_ai.request.model" in attributes
        ):
            return "LLM"
        else:
            return "UNKNOWN"

    def convert_gcp_labels_to_openinference(
        self,
        labels: dict[str, str],
    ) -> dict[str, Any]:
        """
        Convert GCP Cloud Trace labels to OpenInference attributes.

        GCP uses labels (simple string key-value pairs) while OpenInference uses
        a nested attribute structure. This method:
        1. Maps GenAI semantic conventions to OpenInference equivalents
        2. Preserves GCP-specific attributes
        3. Handles type conversions (strings to ints/floats where appropriate)

        Args:
            labels: Dict of GCP label key-value pairs (all strings)

        Returns:
            Dict of OpenInference attributes with proper types and structure
        """
        # Start with all labels as-is
        attributes = dict(labels)

        # Map GenAI semantic conventions to OpenInference
        # These are the common mappings from GCP/GenAI to OpenInference

        # Model name mapping
        if "gen_ai.request.model" in attributes:
            attributes[SpanAttributes.LLM_MODEL_NAME] = attributes[
                "gen_ai.request.model"
            ]

        # Token counts
        if "gen_ai.usage.input_tokens" in attributes:
            try:
                attributes[SpanAttributes.LLM_TOKEN_COUNT_PROMPT] = int(
                    attributes["gen_ai.usage.input_tokens"]
                )
            except (ValueError, TypeError):
                pass

        if "gen_ai.usage.output_tokens" in attributes:
            try:
                attributes[SpanAttributes.LLM_TOKEN_COUNT_COMPLETION] = int(
                    attributes["gen_ai.usage.output_tokens"]
                )
            except (ValueError, TypeError):
                pass

        # Calculate total tokens if both present
        if (
            SpanAttributes.LLM_TOKEN_COUNT_PROMPT in attributes
            and SpanAttributes.LLM_TOKEN_COUNT_COMPLETION in attributes
        ):
            attributes[SpanAttributes.LLM_TOKEN_COUNT_TOTAL] = (
                attributes[SpanAttributes.LLM_TOKEN_COUNT_PROMPT]
                + attributes[SpanAttributes.LLM_TOKEN_COUNT_COMPLETION]
            )

        # System/Provider mapping
        if "gen_ai.system" in attributes:
            attributes[SpanAttributes.LLM_SYSTEM] = attributes["gen_ai.system"]

        # Determine and set span kind based on label presence
        attributes[SpanAttributes.OPENINFERENCE_SPAN_KIND] = self._determine_span_kind(
            attributes
        )

        # Agent name mapping
        if "gen_ai.agent.name" in attributes:
            # For agent spans, we could also set input/output values
            pass  # Agent name is already in attributes

        # Tool name mapping
        if "gen_ai.tool.name" in attributes:
            attributes[SpanAttributes.TOOL_NAME] = attributes["gen_ai.tool.name"]

        if "gen_ai.tool.description" in attributes:
            attributes[SpanAttributes.TOOL_DESCRIPTION] = attributes[
                "gen_ai.tool.description"
            ]

        # Session/Conversation ID mapping
        if "gen_ai.conversation.id" in attributes:
            attributes[SpanAttributes.SESSION_ID] = attributes["gen_ai.conversation.id"]

        # Convert numeric string values to actual numbers for known numeric fields
        numeric_fields = [
            "gen_ai.request.temperature",
            "gen_ai.request.top_p",
            "gen_ai.request.top_k",
            "gen_ai.request.max_tokens",
            "gen_ai.request.presence_penalty",
            "gen_ai.request.frequency_penalty",
        ]

        for field in numeric_fields:
            if field in attributes:
                try:
                    # Detect if it should be int or float
                    if "temperature" in field or "top_p" in field or "penalty" in field:
                        attributes[field] = float(attributes[field])
                    else:
                        attributes[field] = int(attributes[field])
                except (ValueError, TypeError):
                    pass  # Keep as string if conversion fails

        # Explode flat dotted keys into nested structures
        # Example: 'llm.model_name' -> {'llm': {'model_name': value}}
        attributes = self._explode_dotted_keys(attributes)

        return attributes

    def _explode_dotted_keys(self, flat_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Convert flat dotted keys to nested dictionary structure.

        Example:
            {'llm.model_name': 'gpt-4', 'llm.temperature': 0.7}
            ->
            {'llm': {'model_name': 'gpt-4', 'temperature': 0.7}}

        Args:
            flat_dict: Dictionary with potentially dotted keys

        Returns:
            Nested dictionary structure
        """
        # Use benedict to unflatten dot notation
        # Set keypath_separator to / to avoid conflicts with dots
        b = benedict(flat_dict, keypath_separator="/")
        # Unflatten using . as separator
        nested = b.unflatten(separator=".")
        return dict(nested)

    def hex_trace_id_to_hex(self, trace_id: str) -> str:
        """Ensure trace ID is in hex format (it should already be)"""
        return trace_id

    def decimal_span_id_to_hex(self, span_id_decimal: str) -> str:
        """Convert GCP's decimal span ID to hex format"""
        try:
            span_id_int = int(span_id_decimal)
            # Convert to hex without 0x prefix, pad to 16 hex chars (8 bytes)
            return format(span_id_int, "016x")
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert span ID {span_id_decimal} to hex")
            return "0" * 16

    def iso_timestamp_to_datetime(self, iso_string: str) -> datetime:
        """Convert ISO8601 timestamp to datetime object"""
        try:
            # Handle Z suffix or +00:00 suffix
            return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp {iso_string}: {e}")
            return datetime.now()
