import logging
import platform
from enum import Enum

import requests
from amplitude import Amplitude, BaseEvent
from config.telemetry_config import TelemetryConfig
from schemas.enums import RuleType
from utils import utils

AMPLITUDE_CLIENT = Amplitude("ae623bd644a045706785eb01fd21945d")
TELEMETRY_CONFIG = TelemetryConfig()

logging.getLogger("amplitude").setLevel(logging.CRITICAL)


class TelemetryEventTypes(str, Enum):
    SERVER_START_INITIATED = "server_start_initiated"
    SERVER_START_COMPLETED = "server_start_completed"

    TASK_CREATE_INITIATED = "task_create_initiated"
    TASK_CREATE_COMPLETED = "task_create_completed"

    DEFAULT_RULE_CREATE_INITIATED = "default_rule_create_initiated"
    DEFAULT_RULE_FOR_REGEX_CREATE_COMPLETED = "default_rule_for_regex_create_completed"
    DEFAULT_RULE_FOR_KEYWORD_CREATE_COMPLETED = (
        "default_rule_for_keyword_create_completed"
    )
    DEFAULT_RULE_FOR_HALLUCINATION_V2_CREATE_COMPLETED = (
        "default_rule_for_hallucination_v2_create_completed"
    )
    DEFAULT_RULE_FOR_PII_CREATE_COMPLETED = "default_rule_for_pii_create_completed"
    DEFAULT_RULE_FOR_PROMPT_INJECTION_CREATE_COMPLETED = (
        "default_rule_for_prompt_injection_create_completed"
    )
    DEFAULT_RULE_FOR_SENSITIVE_DATA_CREATE_COMPLETED = (
        "default_rule_for_sensitive_data_create_completed"
    )
    DEFAULT_RULE_FOR_TOXICITY_CREATE_COMPLETED = (
        "default_rule_for_toxicity_create_completed"
    )

    TASK_RULE_CREATE_INITIATED = "task_rule_create_initiated"
    TASK_RULE_FOR_REGEX_CREATE_COMPLETED = "task_rule_for_regex_create_completed"
    TASK_RULE_FOR_KEYWORD_CREATE_COMPLETED = "task_rule_for_keyword_create_completed"
    TASK_RULE_FOR_HALLUCINATION_V2_CREATE_COMPLETED = (
        "task_rule_for_hallucination_v2_create_completed"
    )
    TASK_RULE_FOR_PII_CREATE_COMPLETED = "task_rule_for_pii_create_completed"
    TASK_RULE_FOR_PROMPT_INJECTION_CREATE_COMPLETED = (
        "task_rule_for_prompt_injection_create_completed"
    )
    TASK_RULE_FOR_SENSITIVE_DATA_CREATE_COMPLETED = (
        "task_rule_for_sensitive_data_create_completed"
    )
    TASK_RULE_FOR_TOXICITY_CREATE_COMPLETED = "task_rule_for_toxicity_create_completed"


def send_telemetry_event_for_task_rule_create_completed(rule_type: RuleType):
    try:
        event_type_map = {
            RuleType.REGEX: TelemetryEventTypes.TASK_RULE_FOR_REGEX_CREATE_COMPLETED,
            RuleType.KEYWORD: TelemetryEventTypes.TASK_RULE_FOR_KEYWORD_CREATE_COMPLETED,
            RuleType.MODEL_HALLUCINATION_V2: TelemetryEventTypes.TASK_RULE_FOR_HALLUCINATION_V2_CREATE_COMPLETED,
            RuleType.PII_DATA: TelemetryEventTypes.TASK_RULE_FOR_PII_CREATE_COMPLETED,
            RuleType.PROMPT_INJECTION: TelemetryEventTypes.TASK_RULE_FOR_PROMPT_INJECTION_CREATE_COMPLETED,
            RuleType.MODEL_SENSITIVE_DATA: TelemetryEventTypes.TASK_RULE_FOR_SENSITIVE_DATA_CREATE_COMPLETED,
            RuleType.TOXICITY: TelemetryEventTypes.TASK_RULE_FOR_TOXICITY_CREATE_COMPLETED,
        }
        if event_type := (event_type_map.get(rule_type)):
            send_telemetry_event(event_type)
    except Exception as e:
        return


def send_telemetry_event_for_default_rule_create_completed(rule_type: RuleType):
    try:
        event_type_map = {
            RuleType.REGEX: TelemetryEventTypes.DEFAULT_RULE_FOR_REGEX_CREATE_COMPLETED,
            RuleType.KEYWORD: TelemetryEventTypes.DEFAULT_RULE_FOR_KEYWORD_CREATE_COMPLETED,
            RuleType.MODEL_HALLUCINATION_V2: TelemetryEventTypes.DEFAULT_RULE_FOR_HALLUCINATION_V2_CREATE_COMPLETED,
            RuleType.PII_DATA: TelemetryEventTypes.DEFAULT_RULE_FOR_PII_CREATE_COMPLETED,
            RuleType.PROMPT_INJECTION: TelemetryEventTypes.DEFAULT_RULE_FOR_PROMPT_INJECTION_CREATE_COMPLETED,
            RuleType.MODEL_SENSITIVE_DATA: TelemetryEventTypes.DEFAULT_RULE_FOR_SENSITIVE_DATA_CREATE_COMPLETED,
            RuleType.TOXICITY: TelemetryEventTypes.DEFAULT_RULE_FOR_TOXICITY_CREATE_COMPLETED,
        }
        if event_type := (event_type_map.get(rule_type)):
            send_telemetry_event(event_type)
    except Exception as e:
        return


def send_telemetry_event(event_type: TelemetryEventTypes):
    try:
        if not TELEMETRY_CONFIG.ENABLED:
            return

        event = BaseEvent(
            event_type=event_type.value,
            user_id=TELEMETRY_CONFIG.get_instance_id(),
            device_id=platform.node(),
            ip=get_public_ip(),
            platform=platform.machine(),
            os_name=platform.system(),
            os_version=platform.version(),
            app_version=utils.get_genai_engine_version(),
        )
        AMPLITUDE_CLIENT.track(event)
        AMPLITUDE_CLIENT.flush()
    except Exception as e:
        return


def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json")
        return response.json()["ip"]
    except requests.RequestException as e:
        return None
