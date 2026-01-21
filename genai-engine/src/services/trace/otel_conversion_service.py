from typing import Any
from openinference.semconv.trace import SpanAttributes, MessageAttributes, ToolCallAttributes, MessageContentAttributes, OpenInferenceSpanKindValues
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_AGENT_DESCRIPTION,
    GEN_AI_AGENT_ID,
    GEN_AI_AGENT_NAME,
    GEN_AI_INPUT_MESSAGES,
    GEN_AI_OUTPUT_MESSAGES,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_FREQUENCY_PENALTY,
    GEN_AI_REQUEST_MAX_TOKENS,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_REQUEST_PRESENCE_PENALTY,
    GEN_AI_REQUEST_SEED,
    GEN_AI_REQUEST_STOP_SEQUENCES,
    GEN_AI_REQUEST_TEMPERATURE,
    GEN_AI_REQUEST_TOP_K,
    GEN_AI_REQUEST_TOP_P,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_TOOL_CALL_ID,
    GEN_AI_TOOL_DESCRIPTION,
    GEN_AI_TOOL_NAME,
    GEN_AI_TOOL_TYPE,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    GEN_AI_SYSTEM,
)
import json


class OtelConversionService:
    """
    Service for converting OpenTelemetry GenAI spans to OpenInference spans
    """

    AGENT_KIND_PREFIXES = (
        GEN_AI_AGENT_ID,
        GEN_AI_AGENT_NAME,
        GEN_AI_AGENT_DESCRIPTION,
    )

    TOOL_EXECUTION_PREFIXES = (
        GEN_AI_TOOL_NAME,
        GEN_AI_TOOL_DESCRIPTION,
        GEN_AI_TOOL_CALL_ID,
        GEN_AI_TOOL_TYPE,
    )

    def convert_otel_span_to_openinference(self, otlp_span: dict[str, Any]) -> dict[str, Any]:
        """Convert full OTLP span to OpenInference span"""
        openinference_span = otlp_span.copy()
        openinference_span['attributes'] = self._convert_genai_to_openinference(otlp_span['attributes'])
        return openinference_span

    def _convert_genai_to_openinference(self, span_attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Convert OpenTelemetry GenAI span attributes to OpenInference span attributes
        
        Args:
            span_attributes: Dictionary of GenAI span attributes
            
        Returns:
            Dictionary of OpenInference span attributes
        """
        attrs = span_attributes.copy()
        converted_keys = set()
        
        mappers = [
            self._map_provider_and_system,
            self._map_models,
            self._map_span_kind,
            self._map_invocation_parameters,
            self._map_input_messages,
            self._map_output_messages,
            self._map_token_counts,
            self._map_tool_execution,
            self._map_input_value,
            self._map_output_value,
        ]
        
        for mapper in mappers:
            new_attrs, keys = mapper(span_attributes)
            attrs.update(new_attrs)
            converted_keys.update(keys)
        
        # Remove converted GenAI attributes
        for key in converted_keys:
            attrs.pop(key, None)
        
        return attrs

    def _get_and_mark(self, span_attributes: dict[str, Any], key: str, converted_keys: set[str]) -> Any:
        """Get attribute value and mark it as converted"""
        if key in span_attributes:
            converted_keys.add(key)
            return span_attributes[key]
        return None

    def _map_provider_and_system(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map provider and system to openinference attributes"""
        converted_keys = set()
        attrs = {}
        
        provider = self._get_and_mark(span_attributes, GEN_AI_PROVIDER_NAME, converted_keys)
        if provider:
            attrs[SpanAttributes.LLM_PROVIDER] = str(provider)

        system = self._get_and_mark(span_attributes, GEN_AI_SYSTEM, converted_keys)
        if system:
            attrs[SpanAttributes.LLM_SYSTEM] = str(system)
            
        return attrs, converted_keys

    def _map_models(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map model name to openinference attributes"""
        converted_keys = set()
        
        request_model = self._get_and_mark(span_attributes, GEN_AI_REQUEST_MODEL, converted_keys)
        response_model = self._get_and_mark(span_attributes, GEN_AI_RESPONSE_MODEL, converted_keys)
        model_name = response_model or request_model
        
        if not model_name:
            return {}, converted_keys
            
        return {SpanAttributes.LLM_MODEL_NAME: str(model_name)}, converted_keys

    def _map_span_kind(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map span kind to openinference attributes"""
        # Default to LLM
        span_kind = OpenInferenceSpanKindValues.LLM.value
        
        # Detect agent kind
        if any(prefix in span_attributes for prefix in self.AGENT_KIND_PREFIXES):
            span_kind = OpenInferenceSpanKindValues.AGENT.value
        
        # Detect tool execution kind
        if any(prefix in span_attributes for prefix in self.TOOL_EXECUTION_PREFIXES):
            span_kind = OpenInferenceSpanKindValues.TOOL.value
        
        return {SpanAttributes.OPENINFERENCE_SPAN_KIND: span_kind}, set()

    def _map_invocation_parameters(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map invocation parameters to openinference attributes"""
        converted_keys = set()
        invocation_params = {}
        
        param_mappings = [
            (GEN_AI_REQUEST_MODEL, "model", str),
            (GEN_AI_REQUEST_TEMPERATURE, "temperature", float),
            (GEN_AI_REQUEST_TOP_P, "top_p", float),
            (GEN_AI_REQUEST_TOP_K, "top_k", int),
            (GEN_AI_REQUEST_PRESENCE_PENALTY, "presence_penalty", float),
            (GEN_AI_REQUEST_FREQUENCY_PENALTY, "frequency_penalty", float),
            (GEN_AI_REQUEST_SEED, "seed", int),
            (GEN_AI_REQUEST_STOP_SEQUENCES, "stop_sequences", list),
            (GEN_AI_REQUEST_MAX_TOKENS, "max_completion_tokens", int),
        ]
        
        for gen_ai_key, param_key, converter in param_mappings:
            value = self._get_and_mark(span_attributes, gen_ai_key, converted_keys)
            if value is not None:
                invocation_params[param_key] = converter(value)
        
        if not invocation_params:
            return {}, converted_keys
            
        return {SpanAttributes.LLM_INVOCATION_PARAMETERS: invocation_params}, converted_keys

    def _map_input_value(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map input value to openinference attributes"""
        converted_keys = set()
        
        input_val = (self._get_and_mark(span_attributes, "input", converted_keys) or 
                    self._get_and_mark(span_attributes, "gen_ai.prompt", converted_keys))
        
        if not input_val:
            return {}, converted_keys
            
        return {
            SpanAttributes.INPUT_VALUE: str(input_val),
            SpanAttributes.INPUT_MIME_TYPE: self._get_mime_type(input_val)
        }, converted_keys

    def _map_output_value(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map output value to openinference attributes"""
        converted_keys = set()
        
        output_val = (self._get_and_mark(span_attributes, "output", converted_keys) or 
                     self._get_and_mark(span_attributes, "gen_ai.completion", converted_keys))
        
        if not output_val:
            return {}, converted_keys
            
        return {
            SpanAttributes.OUTPUT_VALUE: str(output_val),
            SpanAttributes.OUTPUT_MIME_TYPE: self._get_mime_type(output_val)
        }, converted_keys

    def _map_input_messages(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map input messages to openinference attributes"""
        return self._map_messages(
            span_attributes, 
            GEN_AI_INPUT_MESSAGES, 
            SpanAttributes.LLM_INPUT_MESSAGES
        )

    def _map_output_messages(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map output messages to openinference attributes"""
        return self._map_messages(
            span_attributes, 
            GEN_AI_OUTPUT_MESSAGES, 
            SpanAttributes.LLM_OUTPUT_MESSAGES
        )

    def _map_messages(
        self, 
        span_attributes: dict[str, Any], 
        source_key: str, 
        dest_prefix: str
    ) -> tuple[dict[str, Any], set[str]]:
        """Generic message mapping logic"""
        converted_keys = set()
        messages = self._get_and_mark(span_attributes, source_key, converted_keys)
        
        if not messages:
            return {}, converted_keys
        
        # Parse if string
        if isinstance(messages, str):
            try:
                messages = json.loads(messages)
            except json.JSONDecodeError:
                return {}, converted_keys
        
        if not isinstance(messages, list):
            return {}, converted_keys
        
        attrs = {}
        for msg_idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue
            
            msg_prefix = f"{dest_prefix}.{msg_idx}."
            
            # Set role
            role = msg.get("role")
            if role:
                attrs[f"{msg_prefix}{MessageAttributes.MESSAGE_ROLE}"] = str(role)
            
            # Process parts
            parts = msg.get("parts", [])
            self._process_message_parts(attrs, msg_prefix, parts)
        
        return attrs, converted_keys

    def _process_message_parts(self, attrs: dict[str, Any], msg_prefix: str, parts: list[dict[str, Any]]) -> None:
        """Process message parts and add to attributes"""
        if not isinstance(parts, list):
            return
        
        content_idx = 0
        tool_idx = 0
        
        for part in parts:
            if not isinstance(part, dict):
                continue
            
            part_type = part.get("type")
            if not part_type:
                continue
            
            if part_type == "text":
                content = self._to_string_content(part.get("content"))
                if content:
                    content_prefix = f"{msg_prefix}{MessageAttributes.MESSAGE_CONTENTS}.{content_idx}."
                    attrs[f"{content_prefix}{MessageContentAttributes.MESSAGE_CONTENT_TYPE}"] = "text"
                    attrs[f"{content_prefix}{MessageContentAttributes.MESSAGE_CONTENT_TEXT}"] = content
                    content_idx += 1
            
            elif part_type == "tool_call":
                tool_id = part.get("id")
                tool_name = part.get("name")
                tool_args = part.get("arguments", {})
                
                tool_prefix = f"{msg_prefix}{MessageAttributes.MESSAGE_TOOL_CALLS}.{tool_idx}."
                if tool_id:
                    attrs[f"{tool_prefix}{ToolCallAttributes.TOOL_CALL_ID}"] = str(tool_id)
                if tool_name:
                    attrs[f"{tool_prefix}{ToolCallAttributes.TOOL_CALL_FUNCTION_NAME}"] = str(tool_name)
                if tool_args:
                    attrs[f"{tool_prefix}{ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON}"] = json.dumps(tool_args)
                tool_idx += 1
            
            elif part_type == "tool_call_response":
                tool_id = part.get("id")
                response = self._to_string_content(part.get("response"))
                
                if tool_id:
                    attrs[f"{msg_prefix}{MessageAttributes.MESSAGE_TOOL_CALL_ID}"] = str(tool_id)
                
                if response:
                    content_prefix = f"{msg_prefix}{MessageAttributes.MESSAGE_CONTENTS}.{content_idx}."
                    attrs[f"{content_prefix}{MessageContentAttributes.MESSAGE_CONTENT_TYPE}"] = "text"
                    attrs[f"{content_prefix}{MessageContentAttributes.MESSAGE_CONTENT_TEXT}"] = response
                    content_idx += 1

    def _map_token_counts(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map usage token counts to openinference attributes"""
        converted_keys = set()
        attrs = {}
        
        input_tokens = self._get_and_mark(span_attributes, GEN_AI_USAGE_INPUT_TOKENS, converted_keys)
        if input_tokens is not None:
            attrs[SpanAttributes.LLM_TOKEN_COUNT_PROMPT] = int(input_tokens)
        
        output_tokens = self._get_and_mark(span_attributes, GEN_AI_USAGE_OUTPUT_TOKENS, converted_keys)
        if output_tokens is not None:
            attrs[SpanAttributes.LLM_TOKEN_COUNT_COMPLETION] = int(output_tokens)
        
        if input_tokens is not None and output_tokens is not None:
            attrs[SpanAttributes.LLM_TOKEN_COUNT_TOTAL] = int(input_tokens) + int(output_tokens)
        
        return attrs, converted_keys

    def _map_tool_execution(self, span_attributes: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
        """Map tool execution to openinference attributes"""
        converted_keys = set()
        attrs = {}
        
        tool_name = self._get_and_mark(span_attributes, GEN_AI_TOOL_NAME, converted_keys)
        if tool_name:
            attrs[SpanAttributes.TOOL_NAME] = str(tool_name)
        
        tool_description = self._get_and_mark(span_attributes, GEN_AI_TOOL_DESCRIPTION, converted_keys)
        if tool_description:
            attrs[SpanAttributes.TOOL_DESCRIPTION] = str(tool_description)
        
        tool_call_id = self._get_and_mark(span_attributes, GEN_AI_TOOL_CALL_ID, converted_keys)
        if tool_call_id:
            attrs[ToolCallAttributes.TOOL_CALL_ID] = str(tool_call_id)
        
        return attrs, converted_keys

    @staticmethod
    def _get_mime_type(value: Any) -> str:
        """Determine MIME type of value"""
        if isinstance(value, str):
            try:
                json.loads(value)
                return "application/json"
            except json.JSONDecodeError:
                return "text/plain"
        return "text/plain"

    @staticmethod
    def _to_string_content(value: Any) -> str | None:
        """Convert value to string content"""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)


def main():
    otel_span = json.load(open("/Users/talerez/Downloads/example-otlp-trace.json"))
    conversion_service = OtelConversionService()
    openinference_attributes = conversion_service.convert_otel_span_to_openinference(otel_span)
    print(openinference_attributes)

if __name__ == "__main__":
    main()

