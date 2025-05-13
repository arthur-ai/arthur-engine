from datetime import datetime
import base64


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