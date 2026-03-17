"""
Tests for arthur_observability_sdk.tracer module.
"""

import os
import sys
import pytest
import warnings
from unittest.mock import Mock, call, patch
from pathlib import Path

from arthur_observability_sdk.tracer import TraceHandler


class TestTraceHandlerInit:
    """Tests for TraceHandler.init() method."""

    def test_init_with_all_parameters(
        self,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test initialization with all parameters explicitly provided."""
        TraceHandler.init(
            task_id="test-task",
            api_key="test-key",
            base_url="https://test.arthur.ai",
            service_name="test-service",
        )

        # Check that Resource was created with correct attributes
        mock_resource_create = mock_resource
        call_args = mock_resource_create.call_args
        assert call_args is not None
        attrs = call_args[0][0]
        assert attrs["service.name"] == "test-service"
        assert attrs["arthur.task"] == "test-task"

        # Check that OTLP exporter was created with correct endpoint and headers
        assert mock_otlp_exporter.called
        call_kwargs = mock_otlp_exporter.call_args.kwargs
        assert call_kwargs["endpoint"] == "https://test.arthur.ai/v1/traces"
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"

        # Check that BatchSpanProcessor was created (default)
        assert mock_batch_span_processor.called

        # Check that span processor was added to provider
        assert mock_tracer_provider.add_span_processor.called

        # Check that provider was set globally
        assert mock_set_tracer_provider.called

        # Check that handler is initialized
        assert TraceHandler.is_initialized()

    def test_init_with_env_vars(
        self,
        mock_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test initialization using environment variables."""
        TraceHandler.init(service_name="test-service")

        # Check that Resource was created with env var values
        call_args = mock_resource.call_args
        attrs = call_args[0][0]
        assert attrs["arthur.task"] == "test-task-id"

        # Check that OTLP exporter used env var values
        call_kwargs = mock_otlp_exporter.call_args.kwargs
        assert call_kwargs["endpoint"] == "https://test.arthur.ai/v1/traces"
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-api-key"

    def test_init_params_override_env_vars(
        self,
        mock_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that explicit parameters override environment variables."""
        TraceHandler.init(
            task_id="override-task",
            api_key="override-key",
            base_url="https://override.arthur.ai",
        )

        # Check that overridden values were used
        call_args = mock_resource.call_args
        attrs = call_args[0][0]
        assert attrs["arthur.task"] == "override-task"

        call_kwargs = mock_otlp_exporter.call_args.kwargs
        assert call_kwargs["endpoint"] == "https://override.arthur.ai/v1/traces"
        assert call_kwargs["headers"]["Authorization"] == "Bearer override-key"

    def test_init_missing_task_id(self, clear_env_vars):
        """Test that ValueError is raised when task_id is missing."""
        with pytest.raises(ValueError, match="task_id is required"):
            TraceHandler.init(api_key="test-key")

    def test_init_missing_api_key(self, clear_env_vars):
        """Test that ValueError is raised when api_key is missing."""
        with pytest.raises(ValueError, match="api_key is required"):
            TraceHandler.init(task_id="test-task")

    def test_init_default_base_url(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that default base URL is used when not provided."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        call_kwargs = mock_otlp_exporter.call_args.kwargs
        assert call_kwargs["endpoint"] == "https://app.arthur.ai/v1/traces"

    def test_init_default_service_name(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that default service name is derived from the calling script."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        call_args = mock_resource.call_args
        attrs = call_args[0][0]
        # Service name should be derived from test file (tests/test_tracer)
        # or fallback to arthur-service if unable to determine
        assert "service.name" in attrs
        service_name = attrs["service.name"]
        # Should either be derived from script or use fallback
        assert isinstance(service_name, str) and len(service_name) > 0

    def test_init_strips_trailing_slash_from_base_url(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that trailing slashes are stripped from base_url."""
        TraceHandler.init(
            task_id="test-task",
            api_key="test-key",
            base_url="https://test.arthur.ai/",
        )

        call_kwargs = mock_otlp_exporter.call_args.kwargs
        assert call_kwargs["endpoint"] == "https://test.arthur.ai/v1/traces"

    def test_init_with_simple_processor(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_simple_span_processor,
    ):
        """Test initialization with SimpleSpanProcessor."""
        TraceHandler.init(
            task_id="test-task",
            api_key="test-key",
            use_simple_processor=True,
        )

        # Check that SimpleSpanProcessor was created
        assert mock_simple_span_processor.called

    def test_init_with_custom_resource_attributes(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test initialization with custom resource attributes."""
        TraceHandler.init(
            task_id="test-task",
            api_key="test-key",
            resource_attributes={
                "deployment.environment": "production",
                "service.version": "1.0.0",
            },
        )

        call_args = mock_resource.call_args
        attrs = call_args[0][0]
        assert attrs["deployment.environment"] == "production"
        assert attrs["service.version"] == "1.0.0"
        # Should also include default attributes
        assert "service.name" in attrs  # Service name is auto-derived
        assert attrs["arthur.task"] == "test-task"

    def test_init_already_initialized_warning(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that warning is issued when init is called twice."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TraceHandler.init(task_id="test-task", api_key="test-key")

            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "already initialized" in str(w[0].message)


class TestTraceHandlerShutdown:
    """Tests for TraceHandler.shutdown() method."""

    def test_shutdown_success(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test successful shutdown."""
        TraceHandler.init(task_id="test-task", api_key="test-key")
        mock_tracer_provider.shutdown.return_value = True

        result = TraceHandler.shutdown()

        assert result is True
        assert mock_tracer_provider.shutdown.called
        assert not TraceHandler.is_initialized()

    def test_shutdown_not_initialized_warning(self):
        """Test that warning is issued when shutdown is called without initialization."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = TraceHandler.shutdown()

            assert result is False
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "not initialized" in str(w[0].message)

    def test_shutdown_with_timeout(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test shutdown with custom timeout."""
        TraceHandler.init(task_id="test-task", api_key="test-key")
        mock_tracer_provider.shutdown.return_value = True

        result = TraceHandler.shutdown(timeout_millis=5000)

        assert result is True
        assert mock_tracer_provider.shutdown.called


class TestTraceHandlerIsInitialized:
    """Tests for TraceHandler.is_initialized() method."""

    def test_is_initialized_false_initially(self):
        """Test that is_initialized returns False before init."""
        assert not TraceHandler.is_initialized()

    def test_is_initialized_true_after_init(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that is_initialized returns True after init."""
        TraceHandler.init(task_id="test-task", api_key="test-key")
        assert TraceHandler.is_initialized()

    def test_is_initialized_false_after_shutdown(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that is_initialized returns False after shutdown."""
        TraceHandler.init(task_id="test-task", api_key="test-key")
        TraceHandler.shutdown()
        assert not TraceHandler.is_initialized()


class TestGetDefaultServiceName:
    """Tests for TraceHandler._get_default_service_name() method."""

    def test_get_default_service_name_with_valid_main(self):
        """Test service name derivation with a valid __main__ module."""
        # Create a mock main module with a file path
        mock_main = Mock()
        mock_main.__file__ = "/path/to/my_agent/app.py"

        with patch.dict(sys.modules, {'__main__': mock_main}):
            service_name = TraceHandler._get_default_service_name()
            assert service_name == "my_agent.app"

    def test_get_default_service_name_with_nested_path(self):
        """Test service name derivation with nested directory structure."""
        mock_main = Mock()
        mock_main.__file__ = "/home/user/projects/ai_system/agent_service/main.py"

        with patch.dict(sys.modules, {'__main__': mock_main}):
            service_name = TraceHandler._get_default_service_name()
            assert service_name == "agent_service.main"

    def test_get_default_service_name_root_directory(self):
        """Test service name derivation when script is in root or unclear location."""
        mock_main = Mock()
        mock_main.__file__ = "./script.py"

        with patch.dict(sys.modules, {'__main__': mock_main}):
            service_name = TraceHandler._get_default_service_name()
            assert service_name == "script"

    def test_get_default_service_name_no_main_file(self):
        """Test fallback when __main__ has no __file__ attribute."""
        mock_main = Mock(spec=[])  # No __file__ attribute

        with patch.dict(sys.modules, {'__main__': mock_main}):
            service_name = TraceHandler._get_default_service_name()
            assert service_name == "arthur-service"

    def test_get_default_service_name_no_main_module(self):
        """Test fallback when __main__ module doesn't exist."""
        with patch.dict(sys.modules, {'__main__': None}):
            service_name = TraceHandler._get_default_service_name()
            assert service_name == "arthur-service"

    def test_get_default_service_name_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        mock_main = Mock()
        mock_main.__file__ = Mock(side_effect=Exception("Test error"))

        with patch.dict(sys.modules, {'__main__': mock_main}):
            service_name = TraceHandler._get_default_service_name()
            assert service_name == "arthur-service"
