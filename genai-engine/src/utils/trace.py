"""
Trace utility functions.

This module contains pure utility functions for trace/span processing.
For span normalization and validation, see services.trace.SpanNormalizationService.
"""

import base64
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from openinference.semconv.trace import MessageAttributes, SpanAttributes

from utils.constants import EXPECTED_SPAN_VERSION, SPAN_KIND_LLM, SPAN_VERSION_KEY
from utils.token_count import (
    TokenCountCost,
    compute_cost_from_tokens,
    count_tokens_from_messages,
)

logger = logging.getLogger(__name__)

# Compiled regex patterns for query extraction (all case-insensitive)
_QUERY_PATTERNS = [
    # Direct indicators with optional colon (query, prompt, question, task, request)
    re.compile(
        r"(?:query|prompt|question|task|request):?\s+(.+?)(?:\n|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    # User-specific patterns with optional colon
    re.compile(
        r"user\s+(?:query|prompt|question|asks?|wants?\s+to\s+know|is\s+asking):?\s+(.+?)(?:\n|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    # Context-based patterns (these naturally have prepositions, no colon expected)
    re.compile(
        r"(?:based\s+on|given|answer|respond\s+to|help\s+(?:me\s+)?with)\s+(?:the\s+following:?)?\s*(.+?)(?:\n|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    # Quoted content (direct quotes likely contain the query)
    re.compile(r'"([^"]+)"'),
    re.compile(r"'([^']+)'"),
    # Multi-line patterns with optional colon
    re.compile(
        r"(?:query|prompt):?\s*\n\s*(.+?)(?:\n\n|\n(?=[A-Z])|$)",
        re.IGNORECASE | re.DOTALL,
    ),
    # Questions (anything ending with ?)
    re.compile(r"([^.!?]*\?[^.!?]*)"),
    # Polite requests (please/can you/could you/would you)
    re.compile(
        r"((?:please|can\s+you|could\s+you|would\s+you)\s+[^.!?]*[.!?])",
        re.IGNORECASE,
    ),
]

_WHITESPACE_PATTERN = re.compile(r"\s+")
_PREFIX_PATTERNS = [
    re.compile(
        r"^(?:the\s+)?(?:user\s+)?(?:query|prompt|question|task|request)(?:\s+is)?:?\s*",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:please\s+)?(?:help\s+)?(?:me\s+)?(?:with\s+)?", re.IGNORECASE),
    re.compile(r"^(?:i\s+)?(?:need\s+)?(?:you\s+)?(?:to\s+)?", re.IGNORECASE),
]
_SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?]+")


def clean_extracted_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and formatting.
    Uses compiled regex patterns for better performance.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text string
    """
    if not text:
        return ""

    # Remove extra whitespace and newlines using compiled pattern
    cleaned = _WHITESPACE_PATTERN.sub(" ", text.strip())

    # Remove common prefixes using compiled patterns
    for prefix_pattern in _PREFIX_PATTERNS:
        cleaned = prefix_pattern.sub("", cleaned)

    return cleaned.strip()


def extract_span_features(span_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Extract LLM-specific features from a normalized span dictionary.

    Note: This function expects spans to be normalized by SpanNormalizationService.
    The normalization service handles OTEL format conversion, JSON deserialization,
    and nested structure creation.

    Args:
        span_dict: Dictionary containing span data with normalized nested attributes

    Returns:
        Dictionary containing processed span with extracted LLM features
    """
    try:
        attributes = span_dict.get("attributes", {})

        # Access already-normalized nested messages
        input_messages = get_nested_value(
            attributes,
            SpanAttributes.LLM_INPUT_MESSAGES,
            default=[],
        )
        output_messages = get_nested_value(
            attributes,
            SpanAttributes.LLM_OUTPUT_MESSAGES,
            default=[],
        )

        # Early exit if no conversation data
        if not input_messages:
            return {
                "system_prompt": "",
                "user_query": "",
                "response": "",
                "context": [],
            }

        # Extract system prompt and user query (data is already normalized)
        # Using OpenInference semantic convention constants for message attributes
        system_prompt = next(
            (
                get_nested_value(msg, MessageAttributes.MESSAGE_CONTENT, "")
                for msg in input_messages
                if get_nested_value(msg, MessageAttributes.MESSAGE_ROLE) == "system"
            ),
            "",
        )

        user_query = next(
            (
                get_nested_value(msg, MessageAttributes.MESSAGE_CONTENT, "")
                for msg in input_messages
                if get_nested_value(msg, MessageAttributes.MESSAGE_ROLE) == "user"
            ),
            "",
        )

        # Extract response from output messages
        response = ""
        if output_messages:
            first_output_msg = output_messages[0]
            content = get_nested_value(
                first_output_msg,
                MessageAttributes.MESSAGE_CONTENT,
            )
            tool_calls = get_nested_value(
                first_output_msg,
                MessageAttributes.MESSAGE_TOOL_CALLS,
            )

            if content is not None:
                response = content
            elif tool_calls is not None:
                response = json.dumps(tool_calls)
            else:
                # Fallback: serialize the entire message dict
                response = json.dumps(get_nested_value(first_output_msg, "message", {}))

        # Fuzzy extraction fallback: only if user_query is missing or matches system_prompt
        if (not user_query or user_query == system_prompt) and system_prompt:
            extracted = fuzzy_extract_query(system_prompt)
            if extracted and extracted != system_prompt:
                user_query = extracted

        return {
            "system_prompt": system_prompt,
            "user_query": user_query,
            "response": response,
            "context": input_messages,  # Already properly structured by normalization
        }

    except Exception as e:
        logger.error(f"Error extracting span features: {e}")
        raise e


def fuzzy_extract_query(system_prompt: str) -> str:
    """
    Extract a user query from a system prompt using compiled regex patterns.
    Optimized version with early exits and pattern reuse.

    Args:
        system_prompt: The system prompt text to extract query from

    Returns:
        Extracted query string, or empty string if no query found
    """
    if not system_prompt or len(system_prompt) < 10:
        return ""

    candidates = []

    # Try compiled patterns for better performance
    for pattern in _QUERY_PATTERNS:
        matches = pattern.findall(system_prompt)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ""

            # Use optimized cleaning function
            cleaned = clean_extracted_text(match)
            if cleaned and len(cleaned) > 10:
                candidates.append((cleaned, len(cleaned)))

                # Early exit if we find a good candidate
                if len(cleaned) > 50:
                    return cleaned

    # Fallback: try to extract the first meaningful sentence
    if not candidates:
        sentences = _SENTENCE_SPLIT_PATTERN.split(system_prompt)
        for sentence in sentences:
            cleaned = clean_extracted_text(sentence)
            if cleaned and len(cleaned) > 20:  # Longer threshold for fallback
                candidates.append((cleaned, len(cleaned)))
                break

    if candidates:
        # Return the longest candidate (likely most complete)
        return max(candidates, key=lambda x: x[1])[0]

    return ""


# For timestamps in nanoseconds (OpenTelemetry default)
def timestamp_ns_to_datetime(timestamp_ns: int) -> datetime:
    # Convert nanoseconds to seconds (divide by 1,000,000,000)
    timestamp_s = timestamp_ns / 1_000_000_000
    return datetime.fromtimestamp(timestamp_s)


def value_dict_to_value(value: dict[str, Any]) -> str | int | float | bool | Any:
    """
    Convert a OpenTelemetry-standard value dictionary from string to a value
    """
    if "stringValue" in value:
        return value["stringValue"]
    elif "intValue" in value:
        return int(value["intValue"])
    elif "doubleValue" in value:
        return float(value["doubleValue"])
    elif "boolValue" in value:
        return bool(value["boolValue"])
    else:
        return value


def convert_id_to_hex(id: str) -> str:
    """
    Convert a base64 encoded ID to a hex string
    """
    return base64.b64decode(id).hex()


def clean_status_code(status_code: str) -> str:
    """
    Clean a status code string by converting to OTEL Semantic Conventions format.
    """
    if status_code == "STATUS_CODE_OK":
        return "Ok"
    elif status_code == "STATUS_CODE_ERROR":
        return "Error"
    elif status_code == "STATUS_CODE_UNSET":
        return "Unset"
    else:
        return status_code


def get_nested_value(
    obj: dict[str, Any],
    path: str,
    default: Optional[Any] = None,
) -> Any:
    """
    Safely navigate nested dictionary structure using dot-separated path.

    Args:
        obj: Dictionary to navigate
        path: Dot-separated path (e.g., 'llm.model_name')
        default: Default value to return if path not found (defaults to None)

    Returns:
        Value at the path, or default if not found

    Examples:
        get_nested_value({"a": {"b": 1}}, "a.b") -> 1
        get_nested_value({"a": {"b": 1}}, "a.c") -> None
        get_nested_value({"a": {"b": 1}}, "a.c", default=0) -> 0
        get_nested_value(None, "a.b", default="missing") -> "missing"
    """
    if not isinstance(obj, dict):
        return default

    keys = path.split(".")
    current = obj

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current


def validate_span_version(raw_data: Dict[str, Any]) -> bool:
    """
    Validate that a span's raw data contains the expected version.

    Args:
        raw_data: The raw span data dictionary

    Returns:
        bool: True if the span has the expected version, False otherwise
    """
    if not isinstance(raw_data, dict):
        logger.warning("Span has invalid raw_data format")
        return False

    version = raw_data.get(SPAN_VERSION_KEY)
    if version != EXPECTED_SPAN_VERSION:
        logger.warning(
            f"Span has unexpected version: {version}, expected: {EXPECTED_SPAN_VERSION}",
        )
        return False

    return True


# New functions for span processing


def extract_token_cost_from_span(
    span_raw_data: dict[str, Any],
    span_kind: str | None = None,
) -> TokenCountCost:
    """
    Extract token counts and costs from span attributes.
    Calculates missing token counts and costs from message content when needed.

    Returns:
        TokenCountCost object with token_count and token_cost
    """

    if span_kind is None or span_kind != SPAN_KIND_LLM:
        return TokenCountCost(
            prompt_token_count=None,
            completion_token_count=None,
            total_token_count=None,
            prompt_token_cost=None,
            completion_token_cost=None,
            total_token_cost=None,
        )

    attributes = span_raw_data.get("attributes", {})

    # Extract token counts from attributes
    prompt_tokens = get_nested_value(attributes, SpanAttributes.LLM_TOKEN_COUNT_PROMPT)
    completion_tokens = get_nested_value(
        attributes,
        SpanAttributes.LLM_TOKEN_COUNT_COMPLETION,
    )
    total_tokens = get_nested_value(attributes, SpanAttributes.LLM_TOKEN_COUNT_TOTAL)

    # Extract costs from attributes
    prompt_cost = get_nested_value(attributes, SpanAttributes.LLM_COST_PROMPT)
    completion_cost = get_nested_value(attributes, SpanAttributes.LLM_COST_COMPLETION)
    total_cost = get_nested_value(attributes, SpanAttributes.LLM_COST_TOTAL)

    # Get model name for token/cost calculation
    model_name = get_nested_value(attributes, SpanAttributes.LLM_MODEL_NAME)

    # Track if we computed any token counts (to ensure total is recalculated)
    computed_tokens = False

    # Calculate prompt tokens if missing
    if prompt_tokens is None:
        input_messages = get_nested_value(
            attributes,
            SpanAttributes.LLM_INPUT_MESSAGES,
            default=[],
        )
        if input_messages:
            prompt_tokens = count_tokens_from_messages(input_messages, model_name)
            computed_tokens = True
        else:
            prompt_tokens = 0

    # Calculate completion tokens if missing
    if completion_tokens is None:
        output_messages = get_nested_value(
            attributes,
            SpanAttributes.LLM_OUTPUT_MESSAGES,
            default=[],
        )
        if output_messages:
            # Use all output messages, same as input messages
            completion_tokens = count_tokens_from_messages(output_messages, model_name)
            computed_tokens = True
        else:
            completion_tokens = 0

    # Calculate prompt cost if missing (requires model_name and prompt_tokens)
    if prompt_cost is None and (model_name and prompt_tokens is not None):
        prompt_cost = compute_cost_from_tokens(model_name, input_tokens=prompt_tokens)

    # Calculate completion cost if missing (requires model_name and completion_tokens)
    if completion_cost is None and (model_name and completion_tokens is not None):
        completion_cost = compute_cost_from_tokens(
            model_name,
            output_tokens=completion_tokens,
        )

    # Calculate total tokens: always recalculate if we computed any tokens, or if total is missing
    # This ensures consistency when we estimate missing values
    if computed_tokens or total_tokens is None:
        if prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens

    # Calculate total cost if missing
    if total_cost is None and prompt_cost is not None and completion_cost is not None:
        total_cost = prompt_cost + completion_cost

    return TokenCountCost(
        prompt_token_count=prompt_tokens,
        completion_token_count=completion_tokens,
        total_token_count=total_tokens,
        prompt_token_cost=prompt_cost,
        completion_token_cost=completion_cost,
        total_token_cost=total_cost,
    )


def value_to_string(value: Any) -> Optional[str]:
    """Convert a value to string, handling dicts/lists by JSON serialization.

    This is used to ensure consistent string representation for input/output
    content across spans and trace metadata. The normalizer may parse JSON
    strings into dicts/lists based on mime_type, and this function converts
    them back to strings for storage and API responses.

    Args:
        value: Any value to convert to string

    Returns:
        String representation of the value, or None if value is None
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)
