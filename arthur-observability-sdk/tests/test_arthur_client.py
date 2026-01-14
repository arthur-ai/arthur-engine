"""
Tests for the unified ArthurClient.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID

from arthur_observability_sdk import ArthurClient
from arthur_observability_sdk.telemetry import TelemetryHandler


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("ARTHUR_TASK_ID", "test-task-id")
    monkeypatch.setenv("ARTHUR_API_KEY", "test-api-key")
    monkeypatch.setenv("ARTHUR_BASE_URL", "https://test.arthur.ai")


@pytest.fixture
def arthur_client():
    """Create an ArthurClient instance for testing."""
    with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init'):
        with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient'):
            client = ArthurClient(
                task_id="test-task-id",
                api_key="test-api-key",
                base_url="https://test.arthur.ai"
            )
            yield client


class TestArthurClient:
    """Test suite for ArthurClient."""

    def test_init_with_explicit_params(self):
        """Test initialization with explicit parameters."""
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init') as mock_telemetry_init:
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient') as mock_api_client:
                # Mock the client instance to check that telemetry is enabled later
                mock_client_instance = Mock()
                mock_api_client.return_value = mock_client_instance

                client = ArthurClient(
                    task_id="my-task-id",
                    api_key="my-api-key",
                    base_url="https://app.arthur.ai",
                    service_name="my-service",
                    enable_telemetry=True
                )

                # Verify telemetry was initialized
                mock_telemetry_init.assert_called_once_with(
                    task_id="my-task-id",
                    api_key="my-api-key",
                    base_url="https://app.arthur.ai",
                    service_name="my-service",
                    use_simple_processor=False,
                    resource_attributes=None
                )

                # Verify API client was initialized (initially with telemetry_enabled=False)
                mock_api_client.assert_called_once_with(
                    api_key="my-api-key",
                    base_url="https://app.arthur.ai",
                    telemetry_enabled=False  # Initially disabled, then enabled after telemetry init
                )

                # Verify telemetry was enabled on the client after initialization
                assert mock_client_instance._telemetry_enabled is True

                assert client.task_id == "my-task-id"

    def test_init_with_env_vars(self, mock_env):
        """Test initialization using environment variables."""
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init') as mock_telemetry_init:
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient'):
                client = ArthurClient()

                # Verify credentials came from env vars
                assert client.task_id == "test-task-id"
                mock_telemetry_init.assert_called_once()
                call_args = mock_telemetry_init.call_args
                assert call_args.kwargs["task_id"] == "test-task-id"
                assert call_args.kwargs["api_key"] == "test-api-key"
                assert call_args.kwargs["base_url"] == "https://test.arthur.ai"

    def test_init_missing_task_id_and_task_name(self):
        """Test that missing both task_id and task_name raises ValueError."""
        with pytest.raises(ValueError, match="Either task_id or task_name is required"):
            ArthurClient(api_key="test-api-key")

    def test_init_both_task_id_and_task_name(self):
        """Test that providing both task_id and task_name raises ValueError."""
        with pytest.raises(ValueError, match="Cannot provide both task_id and task_name"):
            ArthurClient(
                task_id="test-task-id",
                task_name="test-task-name",
                api_key="test-api-key"
            )

    def test_init_missing_api_key(self):
        """Test that missing api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key is required"):
            ArthurClient(task_id="test-task-id")

    def test_init_with_task_name(self):
        """Test initialization with task_name (auto-creates task)."""
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init') as mock_telemetry_init:
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient') as mock_api_client:
                # Mock the get_or_create_task method
                mock_client_instance = Mock()
                mock_tasks_api = Mock()
                mock_tasks_api.get_or_create_task.return_value = "resolved-task-id-123"
                mock_client_instance.tasks = mock_tasks_api
                mock_api_client.return_value = mock_client_instance

                client = ArthurClient(
                    task_name="my-test-task",
                    api_key="test-api-key",
                    base_url="http://localhost:3030"
                )

                # Verify get_or_create_task was called with task_name
                mock_tasks_api.get_or_create_task.assert_called_once_with(
                    task_name="my-test-task",
                    is_agentic=True
                )

                # Verify resolved task_id is stored
                assert client.task_id == "resolved-task-id-123"

                # Verify telemetry was initialized with resolved task_id
                mock_telemetry_init.assert_called_once()
                call_args = mock_telemetry_init.call_args
                assert call_args.kwargs["task_id"] == "resolved-task-id-123"

    def test_init_with_task_name_env_var(self, monkeypatch):
        """Test initialization using ARTHUR_TASK_NAME environment variable."""
        monkeypatch.setenv("ARTHUR_TASK_NAME", "env-task-name")
        monkeypatch.setenv("ARTHUR_API_KEY", "test-api-key")

        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init'):
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient') as mock_api_client:
                mock_client_instance = Mock()
                mock_tasks_api = Mock()
                mock_tasks_api.get_or_create_task.return_value = "env-resolved-task-id"
                mock_client_instance.tasks = mock_tasks_api
                mock_api_client.return_value = mock_client_instance

                client = ArthurClient()

                # Verify task was resolved from env var
                mock_tasks_api.get_or_create_task.assert_called_once_with(
                    task_name="env-task-name",
                    is_agentic=True
                )
                assert client.task_id == "env-resolved-task-id"

    def test_init_with_telemetry_disabled(self):
        """Test initialization with telemetry disabled."""
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init') as mock_telemetry_init:
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient') as mock_api_client:
                client = ArthurClient(
                    task_id="test-task-id",
                    api_key="test-api-key",
                    enable_telemetry=False
                )

                # Telemetry should NOT be initialized
                mock_telemetry_init.assert_not_called()

                # API client should be initialized with telemetry_enabled=False
                mock_api_client.assert_called_once()
                call_args = mock_api_client.call_args
                assert call_args.kwargs["telemetry_enabled"] is False

    def test_default_base_url(self):
        """Test that default base_url is localhost:3030."""
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init') as mock_telemetry_init:
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient') as mock_api_client:
                client = ArthurClient(
                    task_id="test-task-id",
                    api_key="test-api-key"
                    # Not providing base_url
                )

                # Verify default base_url was used
                mock_api_client.assert_called_once()
                call_args = mock_api_client.call_args
                assert call_args.kwargs["base_url"] == "http://localhost:3030"

                mock_telemetry_init.assert_called_once()
                telemetry_args = mock_telemetry_init.call_args
                assert telemetry_args.kwargs["base_url"] == "http://localhost:3030"

    def test_telemetry_property(self, arthur_client):
        """Test that telemetry property returns TelemetryHandler class."""
        assert arthur_client.telemetry is TelemetryHandler

    def test_shutdown(self):
        """Test shutdown method."""
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler') as mock_telemetry:
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient') as mock_api_client:
                mock_telemetry.is_initialized.return_value = True
                mock_api_instance = Mock()
                mock_api_client.return_value = mock_api_instance

                client = ArthurClient(
                    task_id="test-task-id",
                    api_key="test-api-key"
                )

                client.shutdown()

                # Verify telemetry shutdown was called
                mock_telemetry.shutdown.assert_called_once()

                # Verify API client shutdown was called
                mock_api_instance.shutdown.assert_called_once()

    def test_context_manager(self):
        """Test ArthurClient as a context manager."""
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler') as mock_telemetry:
            with patch('arthur_observability_sdk.arthur_client.InstrumentedArthurClient') as mock_api_client:
                mock_telemetry.is_initialized.return_value = True
                mock_api_instance = Mock()
                mock_api_client.return_value = mock_api_instance

                with ArthurClient(task_id="test-task-id", api_key="test-api-key") as client:
                    assert isinstance(client, ArthurClient)

                # Verify shutdown was called automatically
                mock_telemetry.shutdown.assert_called_once()
                mock_api_instance.shutdown.assert_called_once()

    def test_client_attribute(self, arthur_client):
        """Test that client attribute provides access to API client."""
        assert hasattr(arthur_client, 'client')
        assert hasattr(arthur_client.client, 'prompts')


class TestInstrumentedPrompts:
    """Test suite for instrumented prompt endpoints."""

    @patch('arthur_observability_sdk.api_client.trace.get_tracer')
    @patch('arthur_observability_sdk.api_client.render_prompt_module.sync_detailed')
    def test_render_prompt_with_telemetry(self, mock_render, mock_get_tracer):
        """Test render_saved_agentic_prompt with telemetry enabled."""
        # Setup mocks
        mock_span = MagicMock()
        mock_span.__enter__ = Mock(return_value=mock_span)
        mock_span.__exit__ = Mock(return_value=False)
        mock_tracer = Mock()
        mock_tracer.start_as_current_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.parsed = True
        mock_response.content = b'{"messages": []}'
        mock_render.return_value = mock_response

        # Create client and call render
        with patch('arthur_observability_sdk.arthur_client.TelemetryHandler.init'):
            with patch('arthur_observability_sdk.api_client.AuthenticatedClient'):
                from arthur_observability_sdk.api_client import PromptsAPI

                prompts_api = PromptsAPI(Mock(), telemetry_enabled=True)
                result = prompts_api.render_saved_agentic_prompt(
                    task_id=UUID("12345678-1234-5678-1234-567812345678"),
                    prompt_name="test_prompt",
                    prompt_version="latest",
                    variables={"key": "value"}
                )

                # Verify span was created
                mock_tracer.start_as_current_span.assert_called_once()
                span_name = mock_tracer.start_as_current_span.call_args[0][0]
                assert span_name == "template prompt: test_prompt"

                # Verify span attributes were set
                assert mock_span.set_attribute.called

                # Verify API was called
                assert mock_render.called

    @patch('arthur_observability_sdk.api_client.render_prompt_module.sync_detailed')
    def test_render_prompt_without_telemetry(self, mock_render):
        """Test render_saved_agentic_prompt with telemetry disabled."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_render.return_value = mock_response

        with patch('arthur_observability_sdk.api_client.AuthenticatedClient'):
            from arthur_observability_sdk.api_client import PromptsAPI

            prompts_api = PromptsAPI(Mock(), telemetry_enabled=False)
            result = prompts_api.render_saved_agentic_prompt(
                task_id=UUID("12345678-1234-5678-1234-567812345678"),
                prompt_name="test_prompt",
                prompt_version="latest",
                variables={"key": "value"}
            )

            # Verify API was called directly without span creation
            assert mock_render.called
