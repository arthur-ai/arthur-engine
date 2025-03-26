import platform
import re
from unittest.mock import patch

import pytest
from amplitude import BaseEvent
from clients.telemetry.telemetry_client import (
    TelemetryEventTypes,
    get_public_ip,
    send_telemetry_event,
    send_telemetry_event_for_default_rule_create_completed,
    send_telemetry_event_for_task_rule_create_completed,
)
from requests import RequestException
from schemas.enums import RuleType


@pytest.fixture
def mock_amplitude_client():
    with patch("clients.telemetry.telemetry_client.AMPLITUDE_CLIENT") as mock:
        yield mock


@pytest.fixture
def mock_telemetry_config():
    with patch("clients.telemetry.telemetry_client.TELEMETRY_CONFIG") as mock:
        mock.ENABLED = True
        mock.get_instance_id.return_value = "test-instance"
        yield mock


@pytest.mark.unit_tests
def test_send_telemetry_event(mock_amplitude_client):
    with (
        patch("platform.node") as mock_node,
        patch("clients.telemetry.telemetry_client.get_public_ip") as mock_ip,
        patch(
            "clients.telemetry.telemetry_client.utils.get_genai_engine_version",
        ) as mock_version,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_CONFIG",
        ) as mock_telemetry_config,
    ):
        mock_telemetry_config.ENABLED = True

        mock_node.return_value = "test-node"
        mock_ip.return_value = "1.2.3.4"
        mock_version.return_value = "1.0.0"

        send_telemetry_event(TelemetryEventTypes.SERVER_START_INITIATED)

        expected_event = BaseEvent(
            event_type=TelemetryEventTypes.SERVER_START_INITIATED.value,
            user_id="test-instance",
            device_id="test-node",
            ip="1.2.3.4",
            platform=platform.machine(),
            os_name=platform.system(),
            os_version=platform.version(),
            app_version="1.0.0",
        )

        mock_amplitude_client.track.assert_called_once()
        mock_amplitude_client.flush.assert_called_once()


@pytest.mark.unit_tests
def test_send_telemetry_event_disabled(mock_amplitude_client, mock_telemetry_config):
    mock_telemetry_config.ENABLED = False
    send_telemetry_event(TelemetryEventTypes.SERVER_START_INITIATED)
    mock_amplitude_client.track.assert_not_called()


@pytest.mark.unit_tests
def test_get_public_ip():
    ip = get_public_ip()
    assert ip is not None
    assert bool(re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", ip))


@pytest.mark.unit_tests
def test_get_public_ip_error():
    with patch("requests.get", side_effect=RequestException):
        assert get_public_ip() is None


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "rule_type,expected_event",
    [
        (RuleType.REGEX, TelemetryEventTypes.TASK_RULE_FOR_REGEX_CREATE_COMPLETED),
        (RuleType.KEYWORD, TelemetryEventTypes.TASK_RULE_FOR_KEYWORD_CREATE_COMPLETED),
        (
            RuleType.MODEL_HALLUCINATION_V2,
            TelemetryEventTypes.TASK_RULE_FOR_HALLUCINATION_V2_CREATE_COMPLETED,
        ),
        (RuleType.PII_DATA, TelemetryEventTypes.TASK_RULE_FOR_PII_CREATE_COMPLETED),
        (
            RuleType.PROMPT_INJECTION,
            TelemetryEventTypes.TASK_RULE_FOR_PROMPT_INJECTION_CREATE_COMPLETED,
        ),
        (
            RuleType.MODEL_SENSITIVE_DATA,
            TelemetryEventTypes.TASK_RULE_FOR_SENSITIVE_DATA_CREATE_COMPLETED,
        ),
        (
            RuleType.TOXICITY,
            TelemetryEventTypes.TASK_RULE_FOR_TOXICITY_CREATE_COMPLETED,
        ),
    ],
)
def test_send_telemetry_event_for_task_rule_create_completed(rule_type, expected_event):
    with patch("clients.telemetry.telemetry_client.send_telemetry_event") as mock_send:
        send_telemetry_event_for_task_rule_create_completed(rule_type)
        mock_send.assert_called_once_with(expected_event)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "rule_type,expected_event",
    [
        (RuleType.REGEX, TelemetryEventTypes.DEFAULT_RULE_FOR_REGEX_CREATE_COMPLETED),
        (
            RuleType.KEYWORD,
            TelemetryEventTypes.DEFAULT_RULE_FOR_KEYWORD_CREATE_COMPLETED,
        ),
        (
            RuleType.MODEL_HALLUCINATION_V2,
            TelemetryEventTypes.DEFAULT_RULE_FOR_HALLUCINATION_V2_CREATE_COMPLETED,
        ),
        (RuleType.PII_DATA, TelemetryEventTypes.DEFAULT_RULE_FOR_PII_CREATE_COMPLETED),
        (
            RuleType.PROMPT_INJECTION,
            TelemetryEventTypes.DEFAULT_RULE_FOR_PROMPT_INJECTION_CREATE_COMPLETED,
        ),
        (
            RuleType.MODEL_SENSITIVE_DATA,
            TelemetryEventTypes.DEFAULT_RULE_FOR_SENSITIVE_DATA_CREATE_COMPLETED,
        ),
        (
            RuleType.TOXICITY,
            TelemetryEventTypes.DEFAULT_RULE_FOR_TOXICITY_CREATE_COMPLETED,
        ),
    ],
)
def test_send_telemetry_event_for_default_rule_create_completed(
    rule_type,
    expected_event,
):
    with patch("clients.telemetry.telemetry_client.send_telemetry_event") as mock_send:
        send_telemetry_event_for_default_rule_create_completed(rule_type)
        mock_send.assert_called_once_with(expected_event)
