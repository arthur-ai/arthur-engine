import re
from unittest.mock import patch

import pytest
from amplitude import BaseEvent
from arthur_common.models.enums import RuleType
from requests import RequestException

from clients.telemetry.telemetry_client import (
    TelemetryEventTypes,
    get_public_ip,
    send_telemetry_event,
    send_telemetry_event_for_default_rule_create_completed,
    send_telemetry_event_for_task_rule_create_completed,
)


@pytest.fixture
def mock_amplitude_client():
    with patch("clients.telemetry.telemetry_client.AMPLITUDE_CLIENT") as mock:
        yield mock


@pytest.fixture
def mock_telemetry_config():
    with patch("clients.telemetry.telemetry_client.TELEMETRY_CONFIG") as mock:
        mock.ENABLED = True
        yield mock


@pytest.mark.unit_tests
def test_send_telemetry_event(mock_amplitude_client):
    with (
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_CONFIG",
        ) as mock_telemetry_config,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_USER_ID",
            "test-instance",
        ) as mock_user_id,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_DEVICE_ID",
            "test-node",
        ) as mock_device_id,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_IP",
            "1.2.3.4",
        ) as mock_ip_addr,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_PLATFORM",
            "test-platform",
        ) as mock_platform,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_OS_NAME",
            "test-os-name",
        ) as mock_os_name,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_OS_VERSION",
            "test-os-version",
        ) as mock_os_version,
        patch(
            "clients.telemetry.telemetry_client.TELEMETRY_APP_VERSION",
            "1.0.0",
        ) as mock_app_version,
    ):
        mock_telemetry_config.ENABLED = True

        event_type_to_send = TelemetryEventTypes.SERVER_START_INITIATED
        send_telemetry_event(event_type_to_send)

        mock_amplitude_client.track.assert_called_once()
        tracked_event = mock_amplitude_client.track.call_args[0][0]

        assert isinstance(tracked_event, BaseEvent)
        assert tracked_event.event_type == event_type_to_send.value
        assert tracked_event.user_id == "test-instance"
        assert tracked_event.device_id == "test-node"
        assert tracked_event.ip == "1.2.3.4"
        assert tracked_event.platform == "test-platform"
        assert tracked_event.os_name == "test-os-name"
        assert tracked_event.os_version == "test-os-version"
        assert tracked_event.app_version == "1.0.0"

        mock_amplitude_client.flush.assert_called_once()


@pytest.mark.unit_tests
def test_send_telemetry_event_disabled(mock_amplitude_client, mock_telemetry_config):
    mock_telemetry_config.ENABLED = False
    send_telemetry_event(TelemetryEventTypes.SERVER_START_INITIATED)
    mock_amplitude_client.track.assert_not_called()


@pytest.mark.unit_tests
def test_get_public_ip():
    with patch("requests.get") as mock_get:
        mock_response = mock_get.return_value
        mock_response.json.return_value = {"ip": "203.0.113.42"}
        mock_response.raise_for_status.return_value = None

        ip = get_public_ip()
        assert ip is not None
        assert bool(re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", ip))
        assert ip == "203.0.113.42"


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
