"""
Tests for arthur_observability_sdk.instrumentors module.
"""

import pytest
import warnings
from unittest.mock import Mock, MagicMock, patch

from arthur_observability_sdk import instrumentors


class MockInstrumentor:
    """Mock instrumentor class for testing."""

    def __init__(self):
        self.is_instrumented_by_opentelemetry = False
        self._instrument_called = False
        self._uninstrument_called = False

    def instrument(self, **kwargs):
        """Mock instrument method."""
        self._instrument_called = True
        self.is_instrumented_by_opentelemetry = True

    def uninstrument(self):
        """Mock uninstrument method."""
        self._uninstrument_called = True
        self.is_instrumented_by_opentelemetry = False


class TestInstrumentOpenAI:
    """Tests for instrument_openai function."""

    def test_instrument_openai_success(self, mocker):
        """Test successful OpenAI instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_openai()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called
        assert mock_instrumentor.is_instrumented_by_opentelemetry

    def test_instrument_openai_with_kwargs(self, mocker):
        """Test OpenAI instrumentation with additional kwargs."""
        mock_instrumentor = MockInstrumentor()
        mock_instrumentor.instrument = Mock()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_openai(custom_param="value")

        mock_instrumentor.instrument.assert_called_once_with(custom_param="value")

    def test_instrument_openai_not_installed(self, mocker):
        """Test error when openinference-instrumentation-openai is not installed."""
        mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            side_effect=ImportError("No module named 'openinference.instrumentation.openai'"),
        )

        with pytest.raises(ImportError, match="openinference-instrumentation-openai is not installed"):
            instrumentors.instrument_openai()

    def test_instrument_openai_already_instrumented(self, mocker):
        """Test warning when OpenAI is already instrumented."""
        mock_instrumentor = MockInstrumentor()
        mock_instrumentor.is_instrumented_by_opentelemetry = True
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            return_value=mock_instrumentor,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = instrumentors.instrument_openai()

            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "already instrumented" in str(w[0].message)


class TestInstrumentLangChain:
    """Tests for instrument_langchain function."""

    def test_instrument_langchain_success(self, mocker):
        """Test successful LangChain instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.LangChainInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_langchain()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called

    def test_instrument_langchain_not_installed(self, mocker):
        """Test error when openinference-instrumentation-langchain is not installed."""
        mocker.patch(
            "arthur_observability_sdk.instrumentors.LangChainInstrumentor",
            side_effect=ImportError("No module named 'openinference.instrumentation.langchain'"),
        )

        with pytest.raises(ImportError, match="openinference-instrumentation-langchain is not installed"):
            instrumentors.instrument_langchain()


class TestInstrumentAnthropic:
    """Tests for instrument_anthropic function."""

    def test_instrument_anthropic_success(self, mocker):
        """Test successful Anthropic instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.AnthropicInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_anthropic()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called

    def test_instrument_anthropic_not_installed(self, mocker):
        """Test error when openinference-instrumentation-anthropic is not installed."""
        mocker.patch(
            "arthur_observability_sdk.instrumentors.AnthropicInstrumentor",
            side_effect=ImportError("No module named 'openinference.instrumentation.anthropic'"),
        )

        with pytest.raises(ImportError, match="openinference-instrumentation-anthropic is not installed"):
            instrumentors.instrument_anthropic()


class TestInstrumentLlamaIndex:
    """Tests for instrument_llama_index function."""

    def test_instrument_llama_index_success(self, mocker):
        """Test successful LlamaIndex instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.LlamaIndexInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_llama_index()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called

    def test_instrument_llama_index_not_installed(self, mocker):
        """Test error when openinference-instrumentation-llama-index is not installed."""
        mocker.patch(
            "arthur_observability_sdk.instrumentors.LlamaIndexInstrumentor",
            side_effect=ImportError("No module named 'openinference.instrumentation.llama_index'"),
        )

        with pytest.raises(ImportError, match="openinference-instrumentation-llama-index is not installed"):
            instrumentors.instrument_llama_index()


class TestInstrumentBedrock:
    """Tests for instrument_bedrock function."""

    def test_instrument_bedrock_success(self, mocker):
        """Test successful Bedrock instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.BedrockInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_bedrock()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called


class TestInstrumentVertexAI:
    """Tests for instrument_vertexai function."""

    def test_instrument_vertexai_success(self, mocker):
        """Test successful VertexAI instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.VertexAIInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_vertexai()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called


class TestInstrumentMistralAI:
    """Tests for instrument_mistralai function."""

    def test_instrument_mistralai_success(self, mocker):
        """Test successful MistralAI instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.MistralAIInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_mistralai()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called


class TestInstrumentGroq:
    """Tests for instrument_groq function."""

    def test_instrument_groq_success(self, mocker):
        """Test successful Groq instrumentation."""
        mock_instrumentor = MockInstrumentor()
        mock_class = mocker.patch(
            "arthur_observability_sdk.instrumentors.GroqInstrumentor",
            return_value=mock_instrumentor,
        )

        result = instrumentors.instrument_groq()

        assert result == mock_instrumentor
        assert mock_instrumentor._instrument_called


class TestInstrumentAll:
    """Tests for instrument_all function."""

    def test_instrument_all_with_all_frameworks(self, mocker):
        """Test instrument_all when all frameworks are available."""
        # Mock all instrumentors
        mock_instrumentors = {
            "openai": MockInstrumentor(),
            "langchain": MockInstrumentor(),
            "anthropic": MockInstrumentor(),
            "llama_index": MockInstrumentor(),
            "bedrock": MockInstrumentor(),
            "vertexai": MockInstrumentor(),
            "mistralai": MockInstrumentor(),
            "groq": MockInstrumentor(),
        }

        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_openai",
            return_value=mock_instrumentors["openai"],
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_langchain",
            return_value=mock_instrumentors["langchain"],
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_anthropic",
            return_value=mock_instrumentors["anthropic"],
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_llama_index",
            return_value=mock_instrumentors["llama_index"],
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_bedrock",
            return_value=mock_instrumentors["bedrock"],
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_vertexai",
            return_value=mock_instrumentors["vertexai"],
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_mistralai",
            return_value=mock_instrumentors["mistralai"],
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_groq",
            return_value=mock_instrumentors["groq"],
        )

        result = instrumentors.instrument_all()

        # All frameworks should be instrumented
        assert len(result) == 8
        assert "openai" in result
        assert "langchain" in result
        assert "anthropic" in result
        assert "llama_index" in result
        assert "bedrock" in result
        assert "vertexai" in result
        assert "mistralai" in result
        assert "groq" in result

    def test_instrument_all_with_some_frameworks_missing(self, mocker):
        """Test instrument_all when some frameworks are not installed."""
        mock_openai = MockInstrumentor()
        mock_langchain = MockInstrumentor()

        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_openai",
            return_value=mock_openai,
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_langchain",
            return_value=mock_langchain,
        )
        # Other frameworks raise ImportError
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_anthropic",
            side_effect=ImportError(),
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_llama_index",
            side_effect=ImportError(),
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_bedrock",
            side_effect=ImportError(),
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_vertexai",
            side_effect=ImportError(),
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_mistralai",
            side_effect=ImportError(),
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_groq",
            side_effect=ImportError(),
        )

        result = instrumentors.instrument_all()

        # Only available frameworks should be instrumented
        assert len(result) == 2
        assert "openai" in result
        assert "langchain" in result
        assert "anthropic" not in result

    def test_instrument_all_with_no_frameworks(self, mocker):
        """Test instrument_all when no frameworks are installed."""
        # All frameworks raise ImportError
        for func_name in [
            "instrument_openai",
            "instrument_langchain",
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

        result = instrumentors.instrument_all()

        # Should return empty dict
        assert len(result) == 0
        assert result == {}

    def test_instrument_all_with_kwargs(self, mocker):
        """Test instrument_all passes kwargs to all instrumentors."""
        mock_openai = MockInstrumentor()
        mock_openai.instrument = Mock()

        mock_instrument_openai = mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_openai",
            return_value=mock_openai,
        )

        # Mock other frameworks to raise ImportError
        for func_name in [
            "instrument_langchain",
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

        result = instrumentors.instrument_all(custom_param="value")

        # Kwargs should be passed through
        mock_instrument_openai.assert_called_once_with(custom_param="value")


class TestUninstrumentation:
    """Tests for uninstrumentation functionality."""

    def test_uninstrument_returned_instance(self, mocker):
        """Test that returned instrumentor can be used to uninstrument."""
        mock_instrumentor = MockInstrumentor()
        mocker.patch(
            "arthur_observability_sdk.instrumentors.OpenAIInstrumentor",
            return_value=mock_instrumentor,
        )

        instrumentor = instrumentors.instrument_openai()
        assert instrumentor.is_instrumented_by_opentelemetry

        instrumentor.uninstrument()
        assert mock_instrumentor._uninstrument_called
        assert not instrumentor.is_instrumented_by_opentelemetry

    def test_uninstrument_all_from_instrument_all(self, mocker):
        """Test uninstrumenting all frameworks returned by instrument_all."""
        mock_openai = MockInstrumentor()
        mock_langchain = MockInstrumentor()

        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_openai",
            return_value=mock_openai,
        )
        mocker.patch(
            "arthur_observability_sdk.instrumentors.instrument_langchain",
            return_value=mock_langchain,
        )

        # Mock others to raise ImportError
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

        instrumentors_dict = instrumentors.instrument_all()

        # Uninstrument all
        for inst in instrumentors_dict.values():
            inst.uninstrument()

        assert mock_openai._uninstrument_called
        assert mock_langchain._uninstrument_called
