"""
Context management for Arthur observability tracing.

This module provides context managers for adding session, user, and metadata
attributes to OpenInference traces.
"""

from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from openinference.instrumentation import using_attributes


@contextmanager
def context(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    **kwargs
):
    """
    Context manager for adding session and user metadata to traces.

    This is a convenience wrapper around openinference.instrumentation.using_attributes
    that allows you to attach session IDs, user IDs, metadata, and tags to all spans
    created within the context.

    Args:
        session_id: Session identifier (e.g., conversation ID, thread ID).
        user_id: User identifier (e.g., user email, user ID).
        metadata: Dictionary of additional metadata to attach to spans.
        tags: List of tags for filtering and categorization.
        **kwargs: Additional attributes to pass through to using_attributes.

    Example:
        >>> from arthur_observability_sdk import context
        >>>
        >>> with context(session_id="session-123", user_id="user-456"):
        ...     # All spans created here will have session and user info
        ...     result = agent.invoke({"input": "Hello"})

        >>> # With additional metadata
        >>> with context(
        ...     session_id="session-123",
        ...     user_id="user-456",
        ...     metadata={"environment": "production", "version": "1.0.0"},
        ...     tags=["important", "customer-facing"]
        ... ):
        ...     result = agent.invoke({"input": "Hello"})
    """
    # Build arguments for using_attributes
    attrs = {}

    if session_id is not None:
        attrs["session_id"] = session_id

    if user_id is not None:
        attrs["user_id"] = user_id

    if metadata is not None:
        attrs["metadata"] = metadata

    if tags is not None:
        attrs["tags"] = tags

    # Add any additional kwargs
    attrs.update(kwargs)

    # Delegate to openinference using_attributes
    with using_attributes(**attrs):
        yield
