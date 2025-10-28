"""
Span normalization service using OpenInference semantic conventions.

This service handles the transformation and normalization of span data
from various formats (OTEL, flat dict) into a standardized nested structure
based on OpenInference semantic conventions.
"""

import copy
import json
import logging

from benedict import benedict

from services.trace.span_semantic_conventions import SpanSemanticConventions
from utils.constants import EXPECTED_SPAN_VERSION, SPAN_VERSION_KEY
from utils.trace import value_dict_to_value

logger = logging.getLogger(__name__)


class SpanNormalizationService:
    """
    Service for normalizing span data using OpenInference semantic conventions.

    This service:
    - Converts OTEL format to nested dict structure
    - Deserializes JSON fields deterministically based on semantic conventions
    - Handles nested message structures
    - Validates span versions
    """

    def __init__(self):
        self.conventions = SpanSemanticConventions()

    def validate_span_version(self, raw_data: dict) -> bool:
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

    def normalize_span_to_nested_dict(self, span: dict) -> dict:
        """
        Normalize span data to nested dictionary structure with selective JSON deserialization.

        This function performs the following transformations:
        1. Converts OTEL format (list of key-value pairs) to flat dict
        2. Deserializes JSON fields based on semantic conventions
        3. Handles nested message.contents with special message_content nesting
        4. Uses benedict to unflatten dot notation to nested structure
        5. Converts numeric keys to lists

        Args:
            span: Raw span dictionary (may have OTEL format attributes)

        Returns:
            Normalized span with nested dictionary structure
        """
        result = copy.deepcopy(span)
        raw_attrs = result.get("attributes", {})

        # Convert OTEL format to flat dict first
        if isinstance(raw_attrs, list):
            attrs = self._convert_otel_to_flat_dict(raw_attrs)
        else:
            attrs = raw_attrs

        # Deserialize JSON fields based on semantic conventions
        attrs = self._deserialize_json_attributes(attrs)

        # Handle message.contents with special nesting for message_content
        attrs = self._handle_message_contents(attrs)

        result["attributes"] = attrs

        # Use benedict to unflatten dot notation to nested dicts for entire span structure
        # Keypath separator is set to / to avoid conflicts with the dot notation.
        b = benedict(result, keypath_separator="/")
        # Unflatten the dot notation to nested dicts.
        # Separator is set to . to match the dot notation.
        b = b.unflatten(separator=".")
        nested = self._convert_numeric_keys_to_lists(b)

        # Deserialize any remaining JSON strings in nested structures (e.g., tool_call arguments)
        try:
            nested = self._deserialize_nested_json_fields(nested)
        except Exception as e:
            logger.error(f"Error deserializing nested JSON fields: {e}", exc_info=True)

        return nested

    def _convert_otel_to_flat_dict(self, raw_attrs: list) -> dict:
        """
        Convert OpenTelemetry format attributes to flat dict with type-aware conversion.

        Single-pass extraction that:
        - Extracts values from OTEL format (stringValue, intValue, etc.)
        - Applies semantic type coercion based on OpenInference conventions
        - Deserializes JSON for known JSON attributes
        - Ensures type correctness per the spec

        Args:
            raw_attrs: List of attribute objects with 'key' and 'value' fields

        Returns:
            Flat dictionary of attributes with spec-compliant types
        """
        attrs = {}

        for attr in raw_attrs:
            key = attr.get("key")
            value_dict = attr.get("value", {})
            if not key:
                continue

            # Get expected type from semantic conventions
            expected_type = self.conventions.get_expected_type(key)

            # Single-pass: extract from OTEL and apply semantic coercion
            attrs[key] = self._extract_and_convert_from_otel(
                value_dict,
                expected_type,
                key,
            )

        return attrs

    def _extract_and_convert_from_otel(
        self,
        value_dict: dict,
        expected_type: str,
        key: str,
    ):
        """
        Extract value from OTEL format and convert to expected type in single pass.

        Args:
            value_dict: OTEL value dictionary (e.g., {"stringValue": "123"})
            expected_type: Expected type from semantic conventions
            key: Attribute key (for logging)

        Returns:
            Properly typed value
        """
        # Extract based on OTEL format
        if "stringValue" in value_dict:
            raw = value_dict["stringValue"]
            return self._convert_string_to_type(raw, expected_type, key)

        elif "intValue" in value_dict:
            raw = int(value_dict["intValue"])
            return self._convert_int_to_type(raw, expected_type, key)

        elif "doubleValue" in value_dict:
            raw = float(value_dict["doubleValue"])
            return self._convert_float_to_type(raw, expected_type, key)

        elif "boolValue" in value_dict:
            raw = bool(value_dict["boolValue"])
            return self._convert_bool_to_type(raw, expected_type, key)

        elif "arrayValue" in value_dict:
            # Arrays are already lists in OTEL format
            return value_dict["arrayValue"]

        elif "kvlistValue" in value_dict:
            # Key-value lists - convert to dict
            return value_dict["kvlistValue"]

        else:
            # Fallback to generic extraction
            return value_dict_to_value(value_dict)

    def _convert_string_to_type(self, value: str, expected_type: str, key: str):
        """Convert string value to expected type based on semantic conventions."""
        if expected_type == "json":
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                logger.debug(f"Failed to parse JSON for '{key}': {value[:100]}")
                return value

        elif expected_type == "int":
            try:
                return int(value)
            except (ValueError, TypeError):
                logger.debug(f"Failed to convert to int for '{key}': {value}")
                return value

        elif expected_type == "float":
            try:
                return float(value)
            except (ValueError, TypeError):
                logger.debug(f"Failed to convert to float for '{key}': {value}")
                return value

        elif expected_type == "bool":
            return value.lower() in ("true", "1", "yes")

        # String or unknown - return as-is
        return value

    def _convert_int_to_type(self, value: int, expected_type: str, key: str):
        """Convert int value to expected type."""
        if expected_type == "float":
            return float(value)
        elif expected_type == "bool":
            return bool(value)
        elif expected_type == "string":
            return str(value)
        # Int or unknown - return as-is
        return value

    def _convert_float_to_type(self, value: float, expected_type: str, key: str):
        """Convert float value to expected type."""
        if expected_type == "int":
            return int(value)
        elif expected_type == "string":
            return str(value)
        # Float or unknown - return as-is
        return value

    def _convert_bool_to_type(self, value: bool, expected_type: str, key: str):
        """Convert bool value to expected type."""
        if expected_type == "string":
            return str(value)
        elif expected_type == "int":
            return int(value)
        # Bool or unknown - return as-is
        return value

    def _deserialize_json_attributes(self, attrs: dict) -> dict:
        """
        Deserialize JSON attributes based on semantic conventions.

        This handles:
        - Non-OTEL format attributes (already flat dict, not from OTEL conversion)
        - Mime type-based JSON detection (input.value with application/json mime_type)

        Note: OTEL format attributes are already type-converted in _convert_otel_to_flat_dict

        Args:
            attrs: Flat dictionary of attributes

        Returns:
            Dictionary with JSON fields deserialized
        """
        result = {}

        for key, value in attrs.items():
            # Check if this should be JSON based on semantic conventions
            mime_type_key = key.replace(".value", ".mime_type")
            mime_type = attrs.get(mime_type_key)

            should_deserialize = self.conventions.should_deserialize_as_json(
                key,
                mime_type,
            )

            if should_deserialize and isinstance(value, str):
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[key] = value
            else:
                result[key] = value

        return result

    def _handle_message_contents(self, attrs: dict) -> dict:
        """
        Handle message.contents with special nesting for message_content.

        This handles the special case where message.contents needs to be
        transformed into a nested structure with message_content objects.

        Args:
            attrs: Dictionary of attributes

        Returns:
            Dictionary with message.contents properly nested
        """
        result = attrs.copy()

        for k in list(result.keys()):
            if k.endswith("message.contents") and isinstance(result[k], str):
                try:
                    contents_list = json.loads(result[k])
                    nested_list = []
                    for item in contents_list:
                        new_item = {}
                        msg_content = {}
                        for ik, iv in item.items():
                            if ik.startswith("message_content."):
                                subkey = ik.split(".", 1)[1]
                                msg_content[subkey] = iv
                            else:
                                new_item[ik] = iv
                        if msg_content:
                            new_item["message_content"] = msg_content
                        nested_list.append(new_item)
                    result[k] = nested_list
                except (json.JSONDecodeError, TypeError):
                    pass

        return result

    def _convert_numeric_keys_to_lists(self, d):
        """
        Recursively convert dictionaries with numeric keys to lists.

        Args:
            d: Dictionary or other data structure to process

        Returns:
            Converted data structure with numeric-keyed dicts converted to lists
        """
        if isinstance(d, dict):
            # Check if all keys are numeric strings
            if all(k.isdigit() for k in d.keys()):
                # Sort by numeric value and convert to list
                return [
                    self._convert_numeric_keys_to_lists(d[k])
                    for k in sorted(d.keys(), key=int)
                ]
            else:
                return {k: self._convert_numeric_keys_to_lists(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self._convert_numeric_keys_to_lists(x) for x in d]
        else:
            return d

    def _deserialize_nested_json_fields(self, obj):
        """
        Recursively deserialize JSON strings in nested structures.

        Specifically handles fields that should be JSON based on semantic conventions:
        - tool_call.function.arguments
        - Any field named 'arguments' within function contexts
        - Any field in the conventions JSON list found at any nesting level

        Args:
            obj: Nested dictionary or list structure

        Returns:
            Structure with JSON strings deserialized
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Check if this key should be deserialized based on conventions
                if self.conventions.should_deserialize_as_json(key) and isinstance(
                    value,
                    str,
                ):
                    try:
                        # Deserialize and then recurse in case the result contains more nested structures
                        deserialized = json.loads(value)
                        result[key] = self._deserialize_nested_json_fields(deserialized)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
                else:
                    result[key] = self._deserialize_nested_json_fields(value)
            return result
        elif isinstance(obj, list):
            return [self._deserialize_nested_json_fields(item) for item in obj]
        else:
            return obj
