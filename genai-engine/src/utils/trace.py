from datetime import datetime
import base64
import logging
import json
import re


logger = logging.getLogger(__name__)

# Compile regex patterns once for better performance
_QUERY_PATTERNS = [
    # Direct query indicators
    re.compile(r'(?:query|Query):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:prompt|Prompt):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:question|Question):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:task|Task):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:request|Request):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    
    # User-specific patterns
    re.compile(r'(?:user query|User query|USER QUERY):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:user prompt|User prompt|USER PROMPT):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:user question|User question|USER QUESTION):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:user asks?|User asks?):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:user wants? to know|User wants? to know):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:user is asking|User is asking):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    
    # Context-based patterns
    re.compile(r'(?:based on the following|Based on the following):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:given the following|Given the following):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:answer the following|Answer the following):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:respond to|Respond to):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:help with|Help with):\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL),
    
    # Quoted content (might be the actual query)
    re.compile(r'"([^"]+)"'),
    re.compile(r"'([^']+)'"),
    
    # Multi-line patterns with newlines
    re.compile(r'(?:query|Query):\s*\n\s*(.+?)(?:\n\n|\n(?=[A-Z])|$)', re.IGNORECASE | re.DOTALL),
    re.compile(r'(?:prompt|Prompt):\s*\n\s*(.+?)(?:\n\n|\n(?=[A-Z])|$)', re.IGNORECASE | re.DOTALL),
    
    # Fallback: look for sentences that seem like questions or requests
    re.compile(r'([^.!?]*\?[^.!?]*)'),  # Questions
    re.compile(r'((?:please|Please|can you|Can you|could you|Could you|would you|Would you)[^.!?]*[.!?])', re.IGNORECASE),  # Polite requests
]

_WHITESPACE_PATTERN = re.compile(r'\s+')
_PREFIX_PATTERNS = [
    re.compile(r'^(?:the\s+)?(?:user\s+)?(?:query|prompt|question|task|request)(?:\s+is)?:?\s*', re.IGNORECASE),
    re.compile(r'^(?:please\s+)?(?:help\s+)?(?:me\s+)?(?:with\s+)?', re.IGNORECASE),
    re.compile(r'^(?:i\s+)?(?:need\s+)?(?:you\s+)?(?:to\s+)?', re.IGNORECASE),
]

# Additional compiled patterns for fallback sentence extraction
_SENTENCE_SPLIT_PATTERN = re.compile(r'[.!?]+')

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
    cleaned = _WHITESPACE_PATTERN.sub(' ', text.strip())
    
    # Remove common prefixes using compiled patterns
    for prefix_pattern in _PREFIX_PATTERNS:
        cleaned = prefix_pattern.sub('', cleaned)
    
    return cleaned.strip()

def extract_span_features(span_dict):
    """
    Extract and clean LLM-specific features from a span dictionary.
    Optimized version with early exits and caching.
    
    Args:
        span_dict: Dictionary containing span data including attributes
        
    Returns:
        Dictionary containing processed span with extracted LLM features
    """
    try:
        attributes = extract_attributes_from_raw_data(span_dict)

        # Extract LLM-specific data
        llm_data = extract_llm_data(attributes)

        # Early exit if no conversation data
        if not llm_data["input_conversation"]:
            return {
                "system_prompt": "",
                "user_query": "",
                "response": "",
                "context": [],
            }

        # Extract data with optimized logic
        system_prompt = ""
        query = ""
        
        # Use more efficient extraction
        for message in llm_data["input_conversation"]:
            if message["role"] == "system" and not system_prompt:
                system_prompt = message.get("content", "")
            elif message["role"] == "user" and not query:
                query = message.get("content", "")
            
            # Early exit if we have both
            if system_prompt and query:
                break
        
        # Extract response more efficiently
        response = ""
        if llm_data["output_conversation"]:
            first_output = llm_data["output_conversation"][0]
            if isinstance(first_output, dict):
                if "content" in first_output:
                    response = first_output["content"]
                elif "tool_calls" in first_output:
                    response = json.dumps(first_output["tool_calls"])
                else:
                    response = json.dumps(first_output)
            else:
                response = str(first_output)
        
        # Only use fuzzy extraction if query is still empty
        if not query and system_prompt:
            query = fuzzy_extract_query(system_prompt)

        return {
            "system_prompt": system_prompt,
            "user_query": query,
            "response": response,
            "context": llm_data["input_conversation"],
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
