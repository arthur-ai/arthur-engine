"""
Semantic conventions helper for OpenInference span attributes.

This module provides type mappings and validation based on OpenInference
semantic conventions to ensure deterministic span normalization.
"""

from openinference.semconv.trace import (
    ChoiceAttributes,
    DocumentAttributes,
    EmbeddingAttributes,
    MessageAttributes,
    MessageContentAttributes,
    PromptAttributes,
    RerankerAttributes,
    SpanAttributes,
    ToolAttributes,
    ToolCallAttributes,
)


class SpanSemanticConventions:
    """
    Helper class for OpenInference semantic conventions.

    Provides type mappings and utilities for deterministic conversion
    of span attributes based on the OpenInference specification.
    """

    # Attributes that should be deserialized as JSON
    # Note: Using OpenInference constants ensures standards compliance
    # The suffix-checking logic in should_deserialize_as_json() handles nested cases
    JSON_ATTRIBUTES = {
        # Span-level JSON attributes
        SpanAttributes.METADATA,
        SpanAttributes.LLM_INVOCATION_PARAMETERS,
        SpanAttributes.LLM_FUNCTION_CALL,
        SpanAttributes.LLM_PROMPT_TEMPLATE_VARIABLES,
        DocumentAttributes.DOCUMENT_METADATA,
        # Tool-level JSON attributes
        SpanAttributes.TOOL_PARAMETERS,
        ToolAttributes.TOOL_JSON_SCHEMA,
        # Message and tool call JSON attributes
        MessageAttributes.MESSAGE_FUNCTION_CALL_ARGUMENTS_JSON,
        ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON,
    }

    # Attributes that are lists of objects (use indexed prefixes)
    LIST_ATTRIBUTES = {
        SpanAttributes.LLM_INPUT_MESSAGES,
        SpanAttributes.LLM_OUTPUT_MESSAGES,
        SpanAttributes.LLM_TOOLS,
        SpanAttributes.LLM_PROMPTS,
        SpanAttributes.LLM_CHOICES,
        SpanAttributes.EMBEDDING_EMBEDDINGS,
        SpanAttributes.RETRIEVAL_DOCUMENTS,
        RerankerAttributes.RERANKER_INPUT_DOCUMENTS,
        RerankerAttributes.RERANKER_OUTPUT_DOCUMENTS,
        MessageAttributes.MESSAGE_TOOL_CALLS,
        MessageAttributes.MESSAGE_CONTENTS,
    }

    # Attributes that should be integers
    INTEGER_ATTRIBUTES = {
        SpanAttributes.LLM_TOKEN_COUNT_PROMPT,
        SpanAttributes.LLM_TOKEN_COUNT_COMPLETION,
        SpanAttributes.LLM_TOKEN_COUNT_TOTAL,
        SpanAttributes.LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_READ,
        SpanAttributes.LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_WRITE,
        SpanAttributes.LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_INPUT,
        SpanAttributes.LLM_TOKEN_COUNT_PROMPT_DETAILS_AUDIO,
        SpanAttributes.LLM_TOKEN_COUNT_COMPLETION_DETAILS_REASONING,
        SpanAttributes.LLM_TOKEN_COUNT_COMPLETION_DETAILS_AUDIO,
        RerankerAttributes.RERANKER_TOP_K,
    }

    # Attributes that should be floats
    FLOAT_ATTRIBUTES = {
        SpanAttributes.LLM_COST_PROMPT,
        SpanAttributes.LLM_COST_COMPLETION,
        SpanAttributes.LLM_COST_TOTAL,
        SpanAttributes.LLM_COST_PROMPT_DETAILS_INPUT,
        SpanAttributes.LLM_COST_PROMPT_DETAILS_CACHE_READ,
        SpanAttributes.LLM_COST_PROMPT_DETAILS_CACHE_WRITE,
        SpanAttributes.LLM_COST_PROMPT_DETAILS_CACHE_INPUT,
        SpanAttributes.LLM_COST_PROMPT_DETAILS_AUDIO,
        SpanAttributes.LLM_COST_COMPLETION_DETAILS_OUTPUT,
        SpanAttributes.LLM_COST_COMPLETION_DETAILS_REASONING,
        SpanAttributes.LLM_COST_COMPLETION_DETAILS_AUDIO,
        DocumentAttributes.DOCUMENT_SCORE,
    }

    # Attributes that should remain as strings
    STRING_ATTRIBUTES = {
        # Span-level string attributes
        SpanAttributes.INPUT_VALUE,
        SpanAttributes.OUTPUT_VALUE,
        SpanAttributes.INPUT_MIME_TYPE,
        SpanAttributes.OUTPUT_MIME_TYPE,
        SpanAttributes.LLM_MODEL_NAME,
        SpanAttributes.LLM_PROVIDER,
        SpanAttributes.LLM_SYSTEM,
        SpanAttributes.EMBEDDING_MODEL_NAME,
        RerankerAttributes.RERANKER_MODEL_NAME,
        RerankerAttributes.RERANKER_QUERY,
        SpanAttributes.TOOL_NAME,
        SpanAttributes.TOOL_DESCRIPTION,
        SpanAttributes.SESSION_ID,
        SpanAttributes.USER_ID,
        SpanAttributes.OPENINFERENCE_SPAN_KIND,
        SpanAttributes.AGENT_NAME,
        SpanAttributes.GRAPH_NODE_ID,
        SpanAttributes.GRAPH_NODE_NAME,
        SpanAttributes.GRAPH_NODE_PARENT_ID,
        SpanAttributes.PROMPT_VENDOR,
        SpanAttributes.PROMPT_ID,
        SpanAttributes.PROMPT_URL,
        # Message attributes
        MessageAttributes.MESSAGE_ROLE,
        MessageAttributes.MESSAGE_CONTENT,
        MessageAttributes.MESSAGE_NAME,
        MessageAttributes.MESSAGE_FUNCTION_CALL_NAME,
        MessageAttributes.MESSAGE_TOOL_CALL_ID,
        # Message content attributes
        MessageContentAttributes.MESSAGE_CONTENT_TYPE,
        MessageContentAttributes.MESSAGE_CONTENT_TEXT,
        # Tool call attributes
        ToolCallAttributes.TOOL_CALL_ID,
        ToolCallAttributes.TOOL_CALL_FUNCTION_NAME,
        # Document attributes
        DocumentAttributes.DOCUMENT_ID,
        DocumentAttributes.DOCUMENT_CONTENT,
        # Embedding attributes
        EmbeddingAttributes.EMBEDDING_TEXT,
        # Prompt and completion attributes
        PromptAttributes.PROMPT_TEXT,
        ChoiceAttributes.COMPLETION_TEXT,
    }

    # Attributes that should be boolean
    BOOLEAN_ATTRIBUTES = {
        # OpenTelemetry standard exception attribute (not OpenInference-specific)
        "exception.escaped",
    }

    # Mime type attributes that indicate value deserialization
    MIME_TYPE_JSON = "application/json"

    @classmethod
    def should_deserialize_as_json(cls, key: str, mime_type: str | None = None) -> bool:
        """
        Determine if an attribute should be deserialized as JSON.

        Args:
            key: The attribute key (may be dot-separated path)
            mime_type: Optional mime type indicator

        Returns:
            True if the attribute should be deserialized as JSON
        """
        # Check if mime_type explicitly indicates JSON
        if mime_type == cls.MIME_TYPE_JSON:
            return True

        # Check full key
        if key in cls.JSON_ATTRIBUTES:
            return True

        # Check key suffix (for nested attributes)
        key_parts = key.split(".")
        if len(key_parts) > 1:
            suffix = key_parts[-1]
            if suffix in cls.JSON_ATTRIBUTES:
                return True

        return False

    @classmethod
    def is_list_attribute(cls, key: str) -> bool:
        """
        Check if an attribute is a list type.

        Args:
            key: The attribute key

        Returns:
            True if the attribute is a list type
        """
        # Check exact match
        if key in cls.LIST_ATTRIBUTES:
            return True

        # Check if it's a nested list attribute (e.g., "llm.input_messages.0.message.tool_calls")
        for list_attr in cls.LIST_ATTRIBUTES:
            if key.startswith(list_attr + "."):
                return True

        return False

    @classmethod
    def get_expected_type(cls, key: str) -> str:
        """
        Get the expected type for an attribute.

        Args:
            key: The attribute key

        Returns:
            Type string: 'json', 'int', 'float', 'bool', 'string', 'list', or 'unknown'
        """
        if key in cls.JSON_ATTRIBUTES:
            return "json"
        if key in cls.LIST_ATTRIBUTES:
            return "list"
        if key in cls.INTEGER_ATTRIBUTES:
            return "int"
        if key in cls.FLOAT_ATTRIBUTES:
            return "float"
        if key in cls.BOOLEAN_ATTRIBUTES:
            return "bool"
        if key in cls.STRING_ATTRIBUTES:
            return "string"

        # Check suffix for nested attributes
        key_parts = key.split(".")
        if len(key_parts) > 1:
            suffix = key_parts[-1]
            if suffix in cls.JSON_ATTRIBUTES:
                return "json"
            if suffix in cls.INTEGER_ATTRIBUTES:
                return "int"
            if suffix in cls.FLOAT_ATTRIBUTES:
                return "float"

        return "unknown"
