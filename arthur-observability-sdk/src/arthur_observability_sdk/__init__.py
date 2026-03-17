"""
Arthur Observability SDK

A unified SDK for Arthur platform APIs and OpenInference tracing.

Example:
    >>> from arthur_observability_sdk import ArthurClient, context, instrument_langchain
    >>>
    >>> # Initialize Arthur client (handles both API and telemetry)
    >>> arthur = ArthurClient(
    ...     task_id="my-task-id",
    ...     api_key="my-api-key",
    ...     base_url="https://app.arthur.ai",
    ...     service_name="my-service"
    ... )
    >>>
    >>> # Use API bindings
    >>> prompt = arthur.client.prompts.render_saved_agentic_prompt(
    ...     task_id=arthur.task_id,
    ...     prompt_name="email_template",
    ...     prompt_version="latest",
    ...     variables={"customer_name": "Alice"}
    ... )
    >>>
    >>> # Auto-instrument your framework
    >>> lc_instrumentor = instrument_langchain()
    >>>
    >>> # Add context for sessions and users
    >>> with context(session_id="session-123", user_id="user-456"):
    ...     result = agent.invoke({"input": "Hello"})
    >>>
    >>> # Cleanup when done
    >>> lc_instrumentor.uninstrument()
    >>> arthur.shutdown()
"""

from .arthur_client import ArthurClient
from .context import context
from .instrumentors import (
    instrument_openai,
    instrument_langchain,
    instrument_anthropic,
    instrument_llama_index,
    instrument_bedrock,
    instrument_vertexai,
    instrument_mistralai,
    instrument_groq,
    instrument_all,
)

__version__ = "0.1.0"

__all__ = [
    # Core client
    "ArthurClient",
    "context",
    # Instrumentors
    "instrument_openai",
    "instrument_langchain",
    "instrument_anthropic",
    "instrument_llama_index",
    "instrument_bedrock",
    "instrument_vertexai",
    "instrument_mistralai",
    "instrument_groq",
    "instrument_all",
    # Version
    "__version__",
]
