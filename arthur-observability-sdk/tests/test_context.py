"""
Tests for arthur_observability_sdk.context module.
"""

import pytest
from unittest.mock import Mock, call

from arthur_observability_sdk.context import context


class TestContext:
    """Tests for the context manager."""

    def test_context_with_session_id(self, mock_using_attributes):
        """Test context manager with session_id only."""
        with context(session_id="test-session"):
            pass

        # Verify using_attributes was called with correct arguments
        mock_using_attributes.assert_called_once_with(session_id="test-session")

    def test_context_with_user_id(self, mock_using_attributes):
        """Test context manager with user_id only."""
        with context(user_id="test-user"):
            pass

        mock_using_attributes.assert_called_once_with(user_id="test-user")

    def test_context_with_session_and_user(self, mock_using_attributes):
        """Test context manager with both session_id and user_id."""
        with context(session_id="test-session", user_id="test-user"):
            pass

        mock_using_attributes.assert_called_once_with(
            session_id="test-session", user_id="test-user"
        )

    def test_context_with_metadata(self, mock_using_attributes):
        """Test context manager with metadata dict."""
        metadata = {"environment": "production", "version": "1.0.0"}
        with context(metadata=metadata):
            pass

        mock_using_attributes.assert_called_once_with(metadata=metadata)

    def test_context_with_tags(self, mock_using_attributes):
        """Test context manager with tags list."""
        tags = ["important", "customer-facing"]
        with context(tags=tags):
            pass

        mock_using_attributes.assert_called_once_with(tags=tags)

    def test_context_with_all_parameters(self, mock_using_attributes):
        """Test context manager with all parameters."""
        metadata = {"key": "value"}
        tags = ["tag1", "tag2"]

        with context(
            session_id="test-session",
            user_id="test-user",
            metadata=metadata,
            tags=tags,
        ):
            pass

        mock_using_attributes.assert_called_once_with(
            session_id="test-session",
            user_id="test-user",
            metadata=metadata,
            tags=tags,
        )

    def test_context_with_additional_kwargs(self, mock_using_attributes):
        """Test context manager with additional keyword arguments."""
        with context(
            session_id="test-session",
            custom_attr="custom_value",
            another_attr=123,
        ):
            pass

        mock_using_attributes.assert_called_once_with(
            session_id="test-session",
            custom_attr="custom_value",
            another_attr=123,
        )

    def test_context_with_no_parameters(self, mock_using_attributes):
        """Test context manager with no parameters."""
        with context():
            pass

        mock_using_attributes.assert_called_once_with()

    def test_context_with_none_values(self, mock_using_attributes):
        """Test that None values are not passed to using_attributes."""
        with context(session_id=None, user_id=None):
            pass

        # Should be called with no arguments since None values are filtered out
        mock_using_attributes.assert_called_once_with()

    def test_context_as_context_manager(self, mock_using_attributes):
        """Test that context works as a proper context manager."""
        # Verify __enter__ and __exit__ are called
        with context(session_id="test-session"):
            assert mock_using_attributes.return_value.__enter__.called

        assert mock_using_attributes.return_value.__exit__.called

    def test_context_nested(self, mock_using_attributes):
        """Test nested context managers."""
        with context(session_id="outer-session"):
            with context(user_id="test-user"):
                pass

        # Should be called twice, once for each context
        assert mock_using_attributes.call_count == 2
        calls = mock_using_attributes.call_args_list
        assert calls[0] == call(session_id="outer-session")
        assert calls[1] == call(user_id="test-user")

    def test_context_with_exception(self, mock_using_attributes):
        """Test that context manager properly handles exceptions."""
        with pytest.raises(ValueError):
            with context(session_id="test-session"):
                raise ValueError("Test error")

        # Context should still exit properly
        assert mock_using_attributes.return_value.__exit__.called

    def test_context_with_complex_metadata(self, mock_using_attributes):
        """Test context with complex nested metadata."""
        metadata = {
            "user": {"id": 123, "name": "Test User"},
            "request": {"url": "/api/test", "method": "POST"},
            "nested": {"deep": {"value": True}},
        }

        with context(metadata=metadata):
            pass

        call_kwargs = mock_using_attributes.call_args.kwargs
        assert call_kwargs["metadata"] == metadata

    def test_context_with_empty_collections(self, mock_using_attributes):
        """Test context with empty metadata dict and tags list."""
        with context(metadata={}, tags=[]):
            pass

        mock_using_attributes.assert_called_once_with(metadata={}, tags=[])
