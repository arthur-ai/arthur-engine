"""
Integration tests for arthur_observability_sdk.

These tests verify that different components work together correctly.
"""

import pytest
import warnings
from unittest.mock import Mock, MagicMock, patch

from arthur_observability_sdk import TraceHandler, context, instrument_openai, instrument_all


class TestFullWorkflow:
    """Test complete SDK workflow."""

    def test_init_instrument_context_workflow(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
        mock_using_attributes,
        mocker,
    ):
        """Test complete workflow: init -> instrument -> context -> shutdown."""
        # Mock OpenAI instrumentor
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_instrumentor.instrument = Mock()
        mock_instrumentor.uninstrument = Mock()
        mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            return_value=mock_instrumentor,
        )

        # 1. Initialize tracing
        TraceHandler.init(
            task_id="test-task",
            api_key="test-key",
            service_name="test-service",
        )
        assert TraceHandler.is_initialized()

        # 2. Instrument framework
        instrumentor = instrument_openai()
        assert mock_instrumentor.instrument.called

        # 3. Use context
        with context(session_id="test-session", user_id="test-user"):
            pass
        mock_using_attributes.assert_called_once()

        # 4. Uninstrument
        instrumentor.uninstrument()
        assert mock_instrumentor.uninstrument.called

        # 5. Shutdown
        result = TraceHandler.shutdown()
        assert result is True
        assert not TraceHandler.is_initialized()

    def test_multiple_contexts_with_same_handler(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
        mock_using_attributes,
    ):
        """Test using multiple contexts with same TraceHandler."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        # Multiple contexts should work
        with context(session_id="session-1"):
            pass

        with context(session_id="session-2"):
            pass

        with context(session_id="session-3"):
            pass

        assert mock_using_attributes.call_count == 3

    def test_nested_contexts(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
        mock_using_attributes,
    ):
        """Test nested contexts."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        with context(session_id="outer-session"):
            with context(user_id="inner-user"):
                pass

        assert mock_using_attributes.call_count == 2

    def test_instrument_all_workflow(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
        mocker,
    ):
        """Test workflow with instrument_all."""
        # Mock multiple instrumentors
        mock_openai = MagicMock()
        mock_openai.uninstrument = Mock()
        mock_langchain = MagicMock()
        mock_langchain.uninstrument = Mock()

        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_openai",
            return_value=mock_openai,
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_langchain",
            return_value=mock_langchain,
        )
        # Mock others to fail
        for func_name in [
            "instrument_anthropic",
            "instrument_llama_index",
            "instrument_bedrock",
            "instrument_vertexai",
            "instrument_mistralai",
            "instrument_groq",
        ]:
            mocker.patch(
                f"arthur_observability_sdk.instrumentors.{func_name}",
                side_effect=ImportError(),
            )

        # Initialize and instrument all
        TraceHandler.init(task_id="test-task", api_key="test-key")
        instrumentors = instrument_all()

        assert len(instrumentors) == 2
        assert "openai" in instrumentors
        assert "langchain" in instrumentors

        # Uninstrument all
        for inst in instrumentors.values():
            inst.uninstrument()

        assert mock_openai.uninstrument.called
        assert mock_langchain.uninstrument.called

        # Shutdown
        TraceHandler.shutdown()


class TestErrorHandling:
    """Test error handling across components."""

    def test_context_without_init(self, mock_using_attributes):
        """Test that context works even without TraceHandler.init (relies on OpenInference)."""
        # Context should still work without init
        with context(session_id="test-session"):
            pass

        mock_using_attributes.assert_called_once()

    def test_instrument_without_init(self, mocker):
        """Test that instrumentation works without TraceHandler.init."""
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_instrumentor.instrument = Mock()
        mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            return_value=mock_instrumentor,
        )

        # Should not raise error
        instrumentor = instrument_openai()
        assert mock_instrumentor.instrument.called

    def test_double_init_warning(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test that double initialization raises warning."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            TraceHandler.init(task_id="test-task", api_key="test-key")
            assert len(w) == 1
            assert "already initialized" in str(w[0].message)

    def test_shutdown_without_init(self):
        """Test shutdown without initialization."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = TraceHandler.shutdown()
            assert result is False
            assert len(w) == 1
            assert "not initialized" in str(w[0].message)


class TestConfigurationCombinations:
    """Test various configuration combinations."""

    def test_simple_processor_workflow(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_simple_span_processor,
    ):
        """Test workflow with SimpleSpanProcessor."""
        TraceHandler.init(
            task_id="test-task",
            api_key="test-key",
            use_simple_processor=True,
        )

        assert mock_simple_span_processor.called
        assert TraceHandler.is_initialized()

        TraceHandler.shutdown()

    def test_custom_resource_attributes(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
    ):
        """Test workflow with custom resource attributes."""
        TraceHandler.init(
            task_id="test-task",
            api_key="test-key",
            resource_attributes={"custom.attr": "value"},
        )

        call_args = mock_resource.call_args[0][0]
        assert call_args["custom.attr"] == "value"
        assert call_args["arthur.task"] == "test-task"

    def test_context_with_all_parameters(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
        mock_using_attributes,
    ):
        """Test context with all possible parameters."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        metadata = {"env": "prod", "version": "1.0"}
        tags = ["important", "customer"]

        with context(
            session_id="test-session",
            user_id="test-user",
            metadata=metadata,
            tags=tags,
            custom_attr="custom",
        ):
            pass

        call_kwargs = mock_using_attributes.call_args.kwargs
        assert call_kwargs["session_id"] == "test-session"
        assert call_kwargs["user_id"] == "test-user"
        assert call_kwargs["metadata"] == metadata
        assert call_kwargs["tags"] == tags
        assert call_kwargs["custom_attr"] == "custom"


class TestImportStructure:
    """Test that imports work correctly."""

    def test_import_from_main_package(self):
        """Test importing from main package."""
        from arthur_observability_sdk import (
            TraceHandler,
            context,
            instrument_openai,
            instrument_langchain,
            instrument_all,
        )

        assert TraceHandler is not None
        assert context is not None
        assert instrument_openai is not None
        assert instrument_langchain is not None
        assert instrument_all is not None

    def test_import_from_submodules(self):
        """Test importing from submodules."""
        from arthur_observability_sdk.tracer import TraceHandler
        from arthur_observability_sdk.context import context
        from arthur_observability_sdk.instrumentors import (
            instrument_openai,
            instrument_all,
        )

        assert TraceHandler is not None
        assert context is not None
        assert instrument_openai is not None
        assert instrument_all is not None

    def test_version_available(self):
        """Test that version is available."""
        from arthur_observability_sdk import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)


class TestConcurrentUsage:
    """Test concurrent usage patterns."""

    def test_multiple_instrumentors(
        self,
        clear_env_vars,
        mock_tracer_provider,
        mock_otlp_exporter,
        mock_set_tracer_provider,
        mock_resource,
        mock_batch_span_processor,
        mocker,
    ):
        """Test using multiple instrumentors simultaneously."""
        TraceHandler.init(task_id="test-task", api_key="test-key")

        # Mock multiple instrumentors
        mock_openai = MagicMock()
        mock_openai.is_instrumented_by_opentelemetry = False
        mock_openai.instrument = Mock()
        mock_openai.uninstrument = Mock()

        mock_langchain = MagicMock()
        mock_langchain.is_instrumented_by_opentelemetry = False
        mock_langchain.instrument = Mock()
        mock_langchain.uninstrument = Mock()

        mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            return_value=mock_openai,
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.LangChainInstrumentor",
            return_value=mock_langchain,
        )

        # Instrument both
        openai_inst = instrument_openai()
        from arthur_observability_sdk.instrumentors import instrument_langchain

        langchain_inst = instrument_langchain()

        assert mock_openai.instrument.called
        assert mock_langchain.instrument.called

        # Both should be able to uninstrument
        openai_inst.uninstrument()
        langchain_inst.uninstrument()

        assert mock_openai.uninstrument.called
        assert mock_langchain.uninstrument.called
