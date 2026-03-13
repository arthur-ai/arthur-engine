"""
Auto-instrumentation helpers for various AI/LLM frameworks.

This module provides convenience functions for instrumenting popular frameworks
with OpenInference. Each function returns the instrumentor instance so users
can call .uninstrument() later if needed.
"""

import warnings
from typing import Optional, Dict, Any


def instrument_openai(**kwargs) -> Any:
    """
    Auto-instrument OpenAI SDK with OpenInference.

    This will automatically trace all OpenAI API calls made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The OpenAI instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-openai is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_openai
        >>>
        >>> # Instrument OpenAI
        >>> openai_instrumentor = instrument_openai()
        >>>
        >>> # Use OpenAI as normal - all calls are traced
        >>> from openai import OpenAI
        >>> client = OpenAI()
        >>> response = client.chat.completions.create(...)
        >>>
        >>> # Later: uninstrument if needed
        >>> openai_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-openai is not installed. "
            "Install it with: pip install arthur-obs-sdk[openai]"
        ) from e

    instrumentor = OpenAIInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("OpenAI is already instrumented", UserWarning)

    return instrumentor


def instrument_langchain(**kwargs) -> Any:
    """
    Auto-instrument LangChain with OpenInference.

    This will automatically trace all LangChain operations (chains, agents, etc.)
    made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The LangChain instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-langchain is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_langchain
        >>>
        >>> # Instrument LangChain
        >>> lc_instrumentor = instrument_langchain()
        >>>
        >>> # Use LangChain as normal - all operations are traced
        >>> from langchain.agents import AgentExecutor
        >>> result = agent_executor.invoke({"input": "Hello"})
        >>>
        >>> # Later: uninstrument if needed
        >>> lc_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-langchain is not installed. "
            "Install it with: pip install arthur-obs-sdk[langchain]"
        ) from e

    instrumentor = LangChainInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("LangChain is already instrumented", UserWarning)

    return instrumentor


def instrument_anthropic(**kwargs) -> Any:
    """
    Auto-instrument Anthropic SDK with OpenInference.

    This will automatically trace all Anthropic API calls made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The Anthropic instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-anthropic is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_anthropic
        >>>
        >>> # Instrument Anthropic
        >>> anthropic_instrumentor = instrument_anthropic()
        >>>
        >>> # Use Anthropic as normal - all calls are traced
        >>> import anthropic
        >>> client = anthropic.Anthropic()
        >>> response = client.messages.create(...)
        >>>
        >>> # Later: uninstrument if needed
        >>> anthropic_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.anthropic import AnthropicInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-anthropic is not installed. "
            "Install it with: pip install arthur-obs-sdk[anthropic]"
        ) from e

    instrumentor = AnthropicInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("Anthropic is already instrumented", UserWarning)

    return instrumentor


def instrument_llama_index(**kwargs) -> Any:
    """
    Auto-instrument LlamaIndex with OpenInference.

    This will automatically trace all LlamaIndex operations made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The LlamaIndex instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-llama-index is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_llama_index
        >>>
        >>> # Instrument LlamaIndex
        >>> llama_instrumentor = instrument_llama_index()
        >>>
        >>> # Use LlamaIndex as normal - all operations are traced
        >>> from llama_index.core import VectorStoreIndex
        >>> index = VectorStoreIndex.from_documents(documents)
        >>> response = index.as_query_engine().query("What is...")
        >>>
        >>> # Later: uninstrument if needed
        >>> llama_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-llama-index is not installed. "
            "Install it with: pip install arthur-obs-sdk[llama-index]"
        ) from e

    instrumentor = LlamaIndexInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("LlamaIndex is already instrumented", UserWarning)

    return instrumentor


def instrument_bedrock(**kwargs) -> Any:
    """
    Auto-instrument AWS Bedrock with OpenInference.

    This will automatically trace all Bedrock API calls made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The Bedrock instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-bedrock is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_bedrock
        >>>
        >>> # Instrument Bedrock
        >>> bedrock_instrumentor = instrument_bedrock()
        >>>
        >>> # Use Bedrock as normal - all calls are traced
        >>> import boto3
        >>> bedrock = boto3.client('bedrock-runtime')
        >>> response = bedrock.invoke_model(...)
        >>>
        >>> # Later: uninstrument if needed
        >>> bedrock_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.bedrock import BedrockInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-bedrock is not installed. "
            "Install it with: pip install arthur-obs-sdk[bedrock]"
        ) from e

    instrumentor = BedrockInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("Bedrock is already instrumented", UserWarning)

    return instrumentor


def instrument_vertexai(**kwargs) -> Any:
    """
    Auto-instrument Google VertexAI with OpenInference.

    This will automatically trace all VertexAI API calls made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The VertexAI instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-vertexai is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_vertexai
        >>>
        >>> # Instrument VertexAI
        >>> vertexai_instrumentor = instrument_vertexai()
        >>>
        >>> # Use VertexAI as normal - all calls are traced
        >>> from vertexai.language_models import TextGenerationModel
        >>> model = TextGenerationModel.from_pretrained("text-bison")
        >>> response = model.predict(...)
        >>>
        >>> # Later: uninstrument if needed
        >>> vertexai_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.vertexai import VertexAIInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-vertexai is not installed. "
            "Install it with: pip install arthur-obs-sdk[vertexai]"
        ) from e

    instrumentor = VertexAIInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("VertexAI is already instrumented", UserWarning)

    return instrumentor


def instrument_mistralai(**kwargs) -> Any:
    """
    Auto-instrument MistralAI SDK with OpenInference.

    This will automatically trace all MistralAI API calls made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The MistralAI instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-mistralai is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_mistralai
        >>>
        >>> # Instrument MistralAI
        >>> mistral_instrumentor = instrument_mistralai()
        >>>
        >>> # Use MistralAI as normal - all calls are traced
        >>> from mistralai.client import MistralClient
        >>> client = MistralClient(api_key="...")
        >>> response = client.chat(...)
        >>>
        >>> # Later: uninstrument if needed
        >>> mistral_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.mistralai import MistralAIInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-mistralai is not installed. "
            "Install it with: pip install arthur-obs-sdk[mistralai]"
        ) from e

    instrumentor = MistralAIInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("MistralAI is already instrumented", UserWarning)

    return instrumentor


def instrument_groq(**kwargs) -> Any:
    """
    Auto-instrument Groq SDK with OpenInference.

    This will automatically trace all Groq API calls made after instrumentation.

    Args:
        **kwargs: Additional configuration options to pass to the instrumentor.

    Returns:
        The Groq instrumentor instance. Call .uninstrument() to disable tracing.

    Raises:
        ImportError: If openinference-instrumentation-groq is not installed.

    Example:
        >>> from arthur_observability_sdk import instrument_groq
        >>>
        >>> # Instrument Groq
        >>> groq_instrumentor = instrument_groq()
        >>>
        >>> # Use Groq as normal - all calls are traced
        >>> from groq import Groq
        >>> client = Groq(api_key="...")
        >>> response = client.chat.completions.create(...)
        >>>
        >>> # Later: uninstrument if needed
        >>> groq_instrumentor.uninstrument()
    """
    try:
        from openinference.instrumentation.groq import GroqInstrumentor
    except ImportError as e:
        raise ImportError(
            "openinference-instrumentation-groq is not installed. "
            "Install it with: pip install arthur-obs-sdk[groq]"
        ) from e

    instrumentor = GroqInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(**kwargs)
    else:
        warnings.warn("Groq is already instrumented", UserWarning)

    return instrumentor


def instrument_all(**kwargs) -> Dict[str, Any]:
    """
    Attempt to instrument all available frameworks.

    This will try to instrument every framework for which the corresponding
    openinference-instrumentation package is installed. Frameworks without
    the package installed will be silently skipped.

    Args:
        **kwargs: Additional configuration options to pass to all instrumentors.

    Returns:
        Dictionary mapping framework names to their instrumentor instances.
        Only successfully instrumented frameworks are included.

    Example:
        >>> from arthur_observability_sdk import instrument_all
        >>>
        >>> # Instrument everything that's installed
        >>> instrumentors = instrument_all()
        >>> # Returns: {"openai": <instrumentor>, "langchain": <instrumentor>, ...}
        >>>
        >>> # Later: selectively uninstrument
        >>> instrumentors["openai"].uninstrument()
        >>>
        >>> # Or uninstrument everything
        >>> for instrumentor in instrumentors.values():
        ...     instrumentor.uninstrument()
    """
    instrumentors = {}

    # Try each framework
    frameworks = [
        ("openai", instrument_openai),
        ("langchain", instrument_langchain),
        ("anthropic", instrument_anthropic),
        ("llama_index", instrument_llama_index),
        ("bedrock", instrument_bedrock),
        ("vertexai", instrument_vertexai),
        ("mistralai", instrument_mistralai),
        ("groq", instrument_groq),
    ]

    for name, instrument_func in frameworks:
        try:
            instrumentor = instrument_func(**kwargs)
            instrumentors[name] = instrumentor
        except ImportError:
            # Silently skip frameworks that aren't installed
            pass

    return instrumentors
