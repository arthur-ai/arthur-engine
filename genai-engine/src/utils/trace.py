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

from openinference.semconv.trace import OpenInferenceMimeTypeValues

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


def extract_span_features(span_dict):
    """
    Extract and clean LLM-specific features from a span dictionary with nested attributes.

    Args:
        span_dict: Dictionary containing span data with nested attributes

    Returns:
        Dictionary containing processed span with extracted LLM features
    """
    try:
        attributes = span_dict.get("attributes", {})

        # Fallback for backward compatibility with OpenTelemetry format
        if isinstance(attributes, list):
            attributes = extract_attributes_from_raw_data(span_dict)

        # Directly access input_messages from nested attributes
        input_messages = get_nested_value(attributes, "llm.input_messages") or []
        output_messages = get_nested_value(attributes, "llm.output_messages") or []

        # Early exit if no conversation data
        if not input_messages:
            return {
                "system_prompt": "",
                "user_query": "",
                "response": "",
                "context": [],
            }

        # Extract system prompt and user query from nested structure
        system_prompt = ""
        user_query = ""

        for msg in input_messages:
            message_obj = msg.get("message", {})
            role = message_obj.get("role")
            content = message_obj.get("content", "")

            if role == "system" and not system_prompt:
                system_prompt = content
            elif role == "user" and not user_query:
                user_query = content

            if system_prompt and user_query:
                break

        # Extract response from output messages
        response = ""
        if output_messages:
            first_output = output_messages[0].get("message", {})
            if "content" in first_output:
                response = first_output["content"]
            elif "tool_calls" in first_output:
                response = json.dumps(first_output["tool_calls"])
            else:
                response = json.dumps(first_output)

        # Fuzzy extraction fallback: only if user_query is missing or matches system_prompt
        if (not user_query or user_query == system_prompt) and system_prompt:
            extracted = fuzzy_extract_query(system_prompt)
            if extracted and extracted != system_prompt:
                user_query = extracted

        return {
            "system_prompt": system_prompt,
            "user_query": user_query,
            "response": response,
            "context": input_messages,
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


def value_dict_to_value(value: dict):
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


def clean_null_values(obj):
    """Remove any null values from a dictionary recursively"""
    if isinstance(obj, dict):
        return {k: clean_null_values(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [clean_null_values(item) for item in obj if item is not None]
    return obj


def extract_llm_data(attributes):
    """
    Extract LLM-specific data from nested span attributes.

    Args:
        attributes: Dictionary containing nested span attributes

    Returns:
        Dictionary containing extracted LLM data
    """
    llm_data = {
        "input": None,
        "output": None,
        "model_name": None,
        "invocation_parameters": None,
        "input_conversation": [],
        "output_conversation": [],
    }

    # Extract input if it exists and is JSON
    input_mime_type = get_nested_value(attributes, "input.mime_type")
    if input_mime_type == OpenInferenceMimeTypeValues.JSON.value:
        input_value = get_nested_value(attributes, "input.value")
        if input_value is not None:
            if isinstance(input_value, str):
                try:
                    llm_data["input"] = json.loads(input_value)
                except json.JSONDecodeError:
                    llm_data["input"] = input_value
            else:
                llm_data["input"] = input_value

    # Extract output if it exists and is JSON
    output_mime_type = get_nested_value(attributes, "output.mime_type")
    if output_mime_type == OpenInferenceMimeTypeValues.JSON.value:
        output_value = get_nested_value(attributes, "output.value")
        if output_value is not None:
            if isinstance(output_value, str):
                try:
                    llm_data["output"] = json.loads(output_value)
                except json.JSONDecodeError:
                    llm_data["output"] = output_value
            else:
                llm_data["output"] = output_value

    # Extract model name and invocation parameters
    llm_data["model_name"] = get_nested_value(attributes, "llm.model_name")
    invocation_params = get_nested_value(attributes, "llm.invocation_parameters")
    if invocation_params is not None:
        if isinstance(invocation_params, str):
            try:
                llm_data["invocation_parameters"] = json.loads(invocation_params)
            except json.JSONDecodeError:
                llm_data["invocation_parameters"] = invocation_params
        else:
            llm_data["invocation_parameters"] = invocation_params

    def extract_tool_calls_from_message(message_data):
        """Extract tool calls from nested message structure.

        Note: Arguments are already deserialized by normalize_span_to_nested_dict.
        """
        tool_calls = []
        tool_calls_data = message_data.get("tool_calls", [])

        if tool_calls_data and isinstance(tool_calls_data, list):
            for i, tool_call_data in enumerate(tool_calls_data):
                if isinstance(tool_call_data, dict):
                    function_data = tool_call_data.get("tool_call", {}).get(
                        "function",
                        {},
                    )
                    if function_data:
                        tool_call = {
                            "index": i,
                            "name": function_data.get("name"),
                            "arguments": function_data.get("arguments"),
                        }
                        if tool_call.get("name") or tool_call.get("arguments"):
                            tool_calls.append(tool_call)

        return tool_calls

    def extract_message_from_nested(message_data, msg_idx, tool_queue=None):
        """Extract a single message from nested structure."""
        message = {"index": msg_idx}

        message_obj = message_data.get("message", {})
        role = message_obj.get("role")
        content = message_obj.get("content")

        if role is not None:
            message["role"] = role
        if content is not None:
            if role == "tool" and tool_queue:
                try:
                    tool_name = tool_queue.pop(0)
                    message["name"] = tool_name
                    message["result"] = content
                except IndexError:
                    message["name"] = "unknown_tool"
                    message["result"] = content
            else:
                message["content"] = content

        # Extract tool calls if this is an assistant message
        if role == "assistant":
            tool_calls = extract_tool_calls_from_message(message_obj)
            if tool_calls:
                message["tool_calls"] = tool_calls

        return message if message else None

    # Extract input messages from nested structure
    input_messages_data = get_nested_value(attributes, "llm.input_messages")
    if input_messages_data and isinstance(input_messages_data, list):
        tool_queue = []
        for msg_idx, msg_data in enumerate(input_messages_data):
            message = extract_message_from_nested(msg_data, msg_idx, tool_queue)
            if message:
                llm_data["input_conversation"].append(message)
                if message.get("role") == "assistant":
                    tool_queue = [tc["name"] for tc in message.get("tool_calls", [])]
                elif message.get("role") != "tool":
                    tool_queue = []

    # Extract output messages from nested structure
    output_messages_data = get_nested_value(attributes, "llm.output_messages")
    if output_messages_data and isinstance(output_messages_data, list):
        tool_queue = []
        for msg_idx, msg_data in enumerate(output_messages_data):
            message = extract_message_from_nested(msg_data, msg_idx, tool_queue)
            if message:
                llm_data["output_conversation"].append(message)
                if message.get("role") == "assistant":
                    tool_queue = [tc["name"] for tc in message.get("tool_calls", [])]
                elif message.get("role") != "tool":
                    tool_queue = []

    return llm_data


def extract_attributes_from_raw_data(span_dict):
    """
    DEPRECATED: Backward compatibility function for OpenTelemetry format.

    New spans are normalized at ingestion using normalize_span_to_nested_dict().
    This function only handles legacy OpenTelemetry format for backward compatibility.

    Args:
        span_dict: Dictionary containing span data with attributes

    Returns:
        dict: Flat or nested attributes
    """
    raw_attributes = span_dict.get("attributes", {})

    # Handle OpenTelemetry format: list of {key: str, value: {...}}
    if isinstance(raw_attributes, list):
        attributes = {}
        for attr in raw_attributes:
            key = attr.get("key")
            value_dict = attr.get("value", {})
            if key:
                attributes[key] = value_dict_to_value(value_dict)
        return attributes

    # Already normalized (nested or flat dict)
    return raw_attributes


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


def get_nested_value(obj, path):
    """
    Safely navigate nested dictionary structure using dot-separated path.

    Args:
        obj: Dictionary to navigate
        path: Dot-separated path (e.g., 'llm.model_name')

    Returns:
        Value at the path, or None if not found
    """
    if not isinstance(obj, dict):
        return None

    keys = path.split(".")
    current = obj

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None

    return current
