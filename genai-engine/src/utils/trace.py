from datetime import datetime
import base64
import logging
import json
import re

logger = logging.getLogger(__name__)

def extract_span_features(span_dict):
    """
    Extract and clean LLM-specific features from a span dictionary.
    
    Args:
        span_dict: Dictionary containing span data including attributes
        
    Returns:
        Dictionary containing processed span with extracted LLM features
    """
    try:
        attributes = extract_attributes_from_raw_data(span_dict)

        # Extract LLM-specific data
        llm_data = extract_llm_data(attributes)

        # Format to expected output
        system_prompt=""
        query=""
        response=""
    
        for message in llm_data["input_conversation"]:
            if message["role"] == "system" and not system_prompt:
                system_prompt = message["content"]
            elif message["role"] == "user" and not query:
                # Get the latest user query
                query = message["content"]
        
        if llm_data["output_conversation"]:
            response = llm_data["output_conversation"][0]
        else:
            response = ""
        context = llm_data["input_conversation"] if llm_data["input_conversation"] else []
        
        if not query:
            logger.warning("No query found in the span. Attempting to fuzzy extract query from system prompt.")
            query = fuzzy_extract_query(system_prompt)

        formatted_llm_data = {
            "system_prompt": system_prompt,
            "user_query": query,
            "response": response,
            "context": context,
        }


        return formatted_llm_data
    
    except Exception as e:
        logger.error(f"Error extracting span features: {e}")
        raise e

def fuzzy_extract_query(system_prompt: str) -> str:
    """
    Extract a user query from a system prompt using fuzzy pattern matching.
    
    Args:
        system_prompt: The system prompt text to extract query from
        
    Returns:
        Extracted query string, or empty string if no query found
    """
    if not system_prompt:
        return ""
    
    # Common patterns that indicate a user query follows
    query_patterns = [
        # Direct query indicators
        r'(?:query|Query):\s*(.+?)(?:\n|$)',
        r'(?:prompt|Prompt):\s*(.+?)(?:\n|$)',
        r'(?:question|Question):\s*(.+?)(?:\n|$)',
        r'(?:task|Task):\s*(.+?)(?:\n|$)',
        r'(?:request|Request):\s*(.+?)(?:\n|$)',
        
        # User-specific patterns
        r'(?:user query|User query|USER QUERY):\s*(.+?)(?:\n|$)',
        r'(?:user prompt|User prompt|USER PROMPT):\s*(.+?)(?:\n|$)',
        r'(?:user question|User question|USER QUESTION):\s*(.+?)(?:\n|$)',
        r'(?:user asks?|User asks?):\s*(.+?)(?:\n|$)',
        r'(?:user wants? to know|User wants? to know):\s*(.+?)(?:\n|$)',
        r'(?:user is asking|User is asking):\s*(.+?)(?:\n|$)',
        
        # Context-based patterns
        r'(?:based on the following|Based on the following):\s*(.+?)(?:\n|$)',
        r'(?:given the following|Given the following):\s*(.+?)(?:\n|$)',
        r'(?:answer the following|Answer the following):\s*(.+?)(?:\n|$)',
        r'(?:respond to|Respond to):\s*(.+?)(?:\n|$)',
        r'(?:help with|Help with):\s*(.+?)(?:\n|$)',
        
        # Quoted content (might be the actual query)
        r'"([^"]+)"',
        r"'([^']+)'",
        
        # Multi-line patterns with newlines
        r'(?:query|Query):\s*\n\s*(.+?)(?:\n\n|\n(?=[A-Z])|$)',
        r'(?:prompt|Prompt):\s*\n\s*(.+?)(?:\n\n|\n(?=[A-Z])|$)',
        
        # Fallback: look for sentences that seem like questions or requests
        r'([^.!?]*\?[^.!?]*)',  # Questions
        r'((?:please|Please|can you|Can you|could you|Could you|would you|Would you)[^.!?]*[.!?])',  # Polite requests
    ]
    
    candidates = []
    
    # Try each pattern
    for pattern in query_patterns:
        matches = re.findall(pattern, system_prompt, re.IGNORECASE | re.DOTALL)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match else ""
            
            # Clean up the extracted text
            cleaned = clean_extracted_text(match)
            if cleaned and len(cleaned) > 10:  # Only consider meaningful extracts
                candidates.append((cleaned, len(cleaned)))
    
    if not candidates:
        # Fallback: try to extract the first meaningful sentence
        sentences = re.split(r'[.!?]+', system_prompt)
        for sentence in sentences:
            cleaned = clean_extracted_text(sentence)
            if cleaned and len(cleaned) > 20:  # Longer threshold for fallback
                candidates.append((cleaned, len(cleaned)))
                break
    
    if candidates:
        # Return the longest candidate (likely most complete)
        return max(candidates, key=lambda x: x[1])[0]
    
    return ""

def clean_extracted_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and formatting.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text string
    """
    if not text:
        return ""
    
    # Remove extra whitespace and newlines
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common prefixes that might have been captured
    prefixes_to_remove = [
        r'^(?:the\s+)?(?:user\s+)?(?:query|prompt|question|task|request)(?:\s+is)?:?\s*',
        r'^(?:please\s+)?(?:help\s+)?(?:me\s+)?(?:with\s+)?',
        r'^(?:i\s+)?(?:need\s+)?(?:you\s+)?(?:to\s+)?',
    ]
    
    for prefix_pattern in prefixes_to_remove:
        cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

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
    Extract LLM-specific data from a span's attributes.
    
    Args:
        span_dict: Dictionary containing span data including attributes
        
    Returns:
        Dictionary containing extracted LLM data
    """
    llm_data = {
        "input": None,
        "output": None,
        "model_name": None,
        "invocation_parameters": None,
        "input_conversation": [],
        "output_conversation": []
    }
    
    # Extract input if it exists and is JSON
    if "input.mime_type" in attributes and attributes["input.mime_type"] == "application/json":
        if "input.value" in attributes:
            llm_data["input"] = json_to_dict(attributes["input.value"])
    
    # Extract output if it exists and is JSON
    if "output.mime_type" in attributes and attributes["output.mime_type"] == "application/json":
        if "output.value" in attributes:
            llm_data["output"] = json_to_dict(attributes["output.value"])
            
    # Extract model name
    llm_data["model_name"] = attributes.get("llm.model_name")
    
    # Extract invocation parameters
    if "llm.invocation_parameters" in attributes:
        llm_data["invocation_parameters"] = json_to_dict(attributes["llm.invocation_parameters"])
    
    def extract_tool_calls(attributes, base_key):
        """
        Extract tool calls from a message's attributes.
        
        Args:
            attributes: Dictionary containing all attributes
            base_key: Base key for the message (e.g., "llm.input_messages.0.message")
            
        Returns:
            List of tool call dictionaries, each containing name and arguments
        """
        TOOL_INDEX_POSITION = 5
        tool_calls = []
        tool_call_keys = [k for k in attributes.keys() 
                         if k.startswith(f"{base_key}.tool_calls.")]
        
        if tool_call_keys:
            # Get unique tool call indices by finding all numbers in the path
            tool_indices = set()
            for key in tool_call_keys:
                parts = key.split(".")
                if parts[TOOL_INDEX_POSITION].isdigit():
                    tool_indices.add(int(parts[TOOL_INDEX_POSITION]))
            
            tool_indices = sorted(tool_indices)
            
            for tool_idx in tool_indices:
                tool_call = {"index": tool_idx}
                
                # Try both possible paths for tool call data
                tool_base_key = f"{base_key}.tool_calls.{tool_idx}.tool_call.function"
                
                if f"{tool_base_key}.name" in attributes:
                    tool_call["name"] = attributes[f"{tool_base_key}.name"]
                if f"{tool_base_key}.arguments" in attributes:
                    tool_call["arguments"] = json_to_dict(attributes[f"{tool_base_key}.arguments"])
                
                if tool_call:  # Only add if we found any tool call data
                    tool_calls.append(tool_call)
        
        return tool_calls

    def extract_message(message_type, msg_idx, tool_queue=None):
        """Helper function to extract a single message with its tool calls"""
        message = {"index": msg_idx}
        base_key = f"llm.{message_type}_messages.{msg_idx}.message"
        
        # Extract basic message fields
        if f"{base_key}.role" in attributes:
            message["role"] = attributes[f"{base_key}.role"]
        if f"{base_key}.content" in attributes:
            content = attributes[f"{base_key}.content"]
            
            # If this is a tool message, get the tool name from the queue
            if message.get("role") == "tool" and tool_queue:
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
        if message.get("role") == "assistant":
            tool_calls = extract_tool_calls(attributes, base_key)
            if tool_calls:
                message["tool_calls"] = tool_calls
        
        return message if message else None
    
    MESSAGE_INDEX_POSITION = 2

    # Extract input messages
    input_keys = [k for k in attributes.keys() if k.startswith("llm.input_messages.")]
    input_indices = sorted(set(int(k.split(".")[MESSAGE_INDEX_POSITION]) for k in input_keys))
    tool_queue = []
    for msg_idx in input_indices:
        message = extract_message("input", msg_idx, tool_queue)
        if message:
            llm_data["input_conversation"].append(message)
            # If this was an assistant message, update the tool queue
            if message.get("role") == "assistant":
                tool_queue = [tool_call["name"] for tool_call in message.get("tool_calls", [])]
            elif message.get("role") != "tool":
                tool_queue = []
    
    # Extract output messages
    output_keys = [k for k in attributes.keys() if k.startswith("llm.output_messages.")]
    output_indices = sorted(set(int(k.split(".")[MESSAGE_INDEX_POSITION]) for k in output_keys))
    tool_queue = []
    for msg_idx in output_indices:
        message = extract_message("output", msg_idx, tool_queue)
        if message:
            llm_data["output_conversation"].append(message)
            # If this was an assistant message, update the tool queue
            if message.get("role") == "assistant":
                tool_queue = [tool_call["name"] for tool_call in message.get("tool_calls", [])]
            elif message.get("role") != "tool":
                tool_queue = []
    
    return llm_data

def extract_attributes_from_raw_data(span_dict):
    """
    Extract attributes from a span dictionary.
    """
    raw_attributes = span_dict.get("attributes", {})
    attributes = {}
    # Convert attributes to flat dictionary format
    if isinstance(raw_attributes, list):
        # Handle OpenTelemetry format: list of {key: str, value: {stringValue: str, ...}}
        
        for attr in raw_attributes:
            key = attr.get("key")
            value_dict = attr.get("value", {})
            if key:
                attributes[key] = value_dict_to_value(value_dict)
    elif isinstance(raw_attributes, dict):
        # Handle already flattened format or convert if needed
        for key, value in raw_attributes.items():
            if isinstance(value, dict) and any(k in value for k in ["stringValue", "intValue", "doubleValue", "boolValue"]):
                # This is still in OpenTelemetry structured format
                attributes[key] = value_dict_to_value(value)
            else:
                # Already converted
                attributes[key] = value
    else:
        attributes = {}

    return attributes

def json_to_dict(json_str):
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return json_str
