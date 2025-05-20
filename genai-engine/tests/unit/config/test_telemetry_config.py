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
