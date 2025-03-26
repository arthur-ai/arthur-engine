import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from config.telemetry_config import TelemetryConfig


@pytest.mark.unit_tests
def test_telemetry_disabled():
    config = TelemetryConfig(ENABLED=False)
    assert config.ENABLED is False


@pytest.mark.unit_tests
def test_telemetry_enabled():
    config = TelemetryConfig(ENABLED=True)
    assert config.ENABLED is True


@pytest.mark.unit_tests
def test_telemetry_config_file_path():
    config = TelemetryConfig(CONFIG_FILE_PATH="/tmp/test_telemetry.json")
    assert config.CONFIG_FILE_PATH == "/tmp/test_telemetry.json"

    default_config = TelemetryConfig()
    assert default_config.CONFIG_FILE_PATH == "~/.arthur_engine/telemetry_config.json"


@pytest.mark.unit_tests
def test_get_instance_id_with_existing_id():
    config = TelemetryConfig(INSTANCE_ID="test-id")
    assert config.get_instance_id() == "test-id"


@pytest.mark.unit_tests
def test_get_instance_id_from_file():
    test_id = "existing-id"
    mock_file_data = json.dumps({"instance_id": test_id})

    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.open", mock_open(read_data=mock_file_data)),
        patch("pathlib.Path.expanduser") as mock_expanduser,
    ):
        mock_exists.return_value = True
        mock_expanduser.return_value = Path("/tmp/fake/path")

        config = TelemetryConfig()
        assert config.get_instance_id() == test_id


@pytest.mark.unit_tests
def test_get_instance_id_creates_new():
    test_uuid = "test-uuid"

    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.open", mock_open()),
        patch("pathlib.Path.expanduser") as mock_expanduser,
        patch("uuid.uuid4") as mock_uuid,
        patch("pathlib.Path.mkdir") as mock_mkdir,
    ):
        mock_exists.return_value = False
        mock_expanduser.return_value = Path("/tmp/fake/path")
        mock_uuid.return_value = test_uuid

        config = TelemetryConfig()
        instance_id = config.get_instance_id()

        assert instance_id == str(test_uuid)
        mock_mkdir.assert_called_once_with(exist_ok=True)


@pytest.mark.unit_tests
def test_get_instance_id_handles_corrupt_file():
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.open", mock_open(read_data="invalid json")),
        patch("pathlib.Path.expanduser") as mock_expanduser,
        patch("pathlib.Path.unlink") as mock_unlink,
        patch("uuid.uuid4") as mock_uuid,
    ):
        mock_exists.return_value = True
        mock_expanduser.return_value = Path("/tmp/fake/path")
        test_uuid = "new-uuid"
        mock_uuid.return_value = test_uuid

        config = TelemetryConfig()
        instance_id = config.get_instance_id()

        assert instance_id == str(test_uuid)
        mock_unlink.assert_called_once_with(missing_ok=True)
