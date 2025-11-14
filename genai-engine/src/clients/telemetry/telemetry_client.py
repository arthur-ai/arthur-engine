import logging
import platform
import uuid
from enum import Enum

import requests
from amplitude import Amplitude, BaseEvent
from arthur_common.models.enums import RuleType

from config.telemetry_config import TelemetryConfig
from utils import utils

logging.getLogger("amplitude").setLevel(logging.CRITICAL)

AMPLITUDE_CLIENT = Amplitude("ae623bd644a045706785eb01fd21945d")
TELEMETRY_CONFIG = TelemetryConfig()


def get_public_ip() -> str | None:
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()
        if ip := response.json().get("ip"):
            return str(ip)
    except requests.RequestException:
        return None
    except ValueError:
        return None
    return None


TELEMETRY_IP: str | None = get_public_ip()
TELEMETRY_USER_ID: str | None = None
TELEMETRY_DEVICE_ID: str | None = None
TELEMETRY_PLATFORM: str | None = None
TELEMETRY_OS_NAME: str | None = None
TELEMETRY_OS_VERSION: str | None = None
TELEMETRY_APP_VERSION: str | None = None
try:
    TELEMETRY_USER_ID = ":".join(
        ["{:02x}".format((uuid.getnode() >> ele) & 0xFF) for ele in range(0, 8 * 6, 8)][
            ::-1
        ],
    )
    TELEMETRY_DEVICE_ID = platform.node()
    TELEMETRY_PLATFORM = platform.machine()
    TELEMETRY_OS_NAME = platform.system()
    TELEMETRY_OS_VERSION = platform.version()
    TELEMETRY_APP_VERSION = utils.get_genai_engine_version()
except Exception:
    pass


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


def send_telemetry_event_for_task_rule_create_completed(rule_type: RuleType) -> None:
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


def send_telemetry_event_for_default_rule_create_completed(rule_type: RuleType) -> None:
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


def send_telemetry_event(event_type: TelemetryEventTypes) -> None:
    if not TELEMETRY_CONFIG.ENABLED:
        return

    event = BaseEvent(
        event_type=event_type.value,
        user_id=TELEMETRY_USER_ID,
        device_id=TELEMETRY_DEVICE_ID,
        ip=TELEMETRY_IP,
        platform=TELEMETRY_PLATFORM,
        os_name=TELEMETRY_OS_NAME,
        os_version=TELEMETRY_OS_VERSION,
        app_version=TELEMETRY_APP_VERSION,
    )

    try:
        AMPLITUDE_CLIENT.track(event)
        AMPLITUDE_CLIENT.flush()
    except Exception as e:
        return
