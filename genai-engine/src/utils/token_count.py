import logging
from typing import List, Optional, Union

import tiktoken
from pydantic import BaseModel
from tokencost import (
    calculate_cost_by_tokens,
    count_message_tokens,
    count_string_tokens,
)

logger = logging.getLogger(__name__)

TIKTOKEN_ENCODER = "cl100k_base"


class TokenCountCost(BaseModel):
    """Data structure for token counts and costs."""

    prompt_token_cost: Optional[float] = None
    completion_token_cost: Optional[float] = None
    total_token_cost: Optional[float] = None
    prompt_token_count: Optional[int] = None
    completion_token_count: Optional[int] = None
    total_token_count: Optional[int] = None


class TokenCounter:
    # Chunk size for processing long texts (words)
    CHUNK_SIZE = 1000

    def __init__(self, model: str = TIKTOKEN_ENCODER):
        """Initializes a titoken encoder

        :param model: tiktoken model encoder
        """
        self.encoder = tiktoken.get_encoding(model)

    def count(self, query: str):
        """Returns token count of the query using chunking for long texts.

        :param query: string query sent to LLM
        """
        if not query:
            return 0

        # Split into words
        words = query.split()

        # For short texts, encode directly
        if len(words) <= self.CHUNK_SIZE:
            return len(self.encoder.encode(query))

        # For long texts, process in word-based chunks
        total_tokens = 0
        for i in range(0, len(words), self.CHUNK_SIZE):
            chunk_words = words[i : i + self.CHUNK_SIZE]
            chunk_text = " ".join(chunk_words)
            total_tokens += len(self.encoder.encode(chunk_text))

        return total_tokens


def compute_cost_from_tokens(
    model_name: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Optional[float]:
    """
    Compute cost from token counts.

    Args:
        model_name: The model name (e.g., "gpt-4", "claude-3-opus")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost or None if computation fails
    """
    try:
        total_cost = 0.0

        # Calculate prompt token cost if input_tokens provided
        if input_tokens > 0:
            prompt_cost = calculate_cost_by_tokens(
                num_tokens=input_tokens,
                model=model_name,
                token_type="input",
            )
            total_cost += float(prompt_cost)

        # Calculate completion token cost if output_tokens provided
        if output_tokens > 0:
            completion_cost = calculate_cost_by_tokens(
                num_tokens=output_tokens,
                model=model_name,
                token_type="output",
            )
            total_cost += float(completion_cost)

        return total_cost if (input_tokens > 0 or output_tokens > 0) else None

    except Exception as e:
        logger.warning(
            f"Error computing cost for model {model_name}: {e}",
        )
        return None


def count_tokens_from_string(
    text: str,
    model_name: Optional[str] = None,
) -> Optional[int]:
    """Calculate token count from string using tokencost or fallback to tiktoken."""
    if not text:
        return None
    try:
        if model_name:
            return count_string_tokens(prompt=text, model=model_name)
        else:
            # Fallback: use default tiktoken encoder
            counter = TokenCounter(TIKTOKEN_ENCODER)
            return counter.count(text)
    except Exception as e:
        logger.warning(f"Error counting tokens from string: {e}")
        return None


def count_tokens_from_messages(
    messages: List[dict],
    model_name: Optional[str] = None,
) -> Optional[int]:
    """Calculate token count from messages using tokencost or fallback to tiktoken.

    Expects OpenInference normalized format where each message has nested structure:
    {"message": {"role": "user", "content": "..."}}
    """
    if not messages:
        return None

    try:
        formatted = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            message_data = msg.get("message", {})
            role = message_data.get("role")
            content = message_data.get("content")

            # Only include messages with content
            if content:
                formatted.append(
                    {"role": str(role) if role else "user", "content": str(content)},
                )

        if not formatted:
            return None

        if model_name:
            # Use tokencost for model-specific counting
            return count_message_tokens(formatted, model=model_name)
        else:
            # Fallback: concatenate message content and use string counter
            combined_text = "\n".join(
                f"{msg['role']}: {msg['content']}" for msg in formatted
            )
            return count_tokens_from_string(combined_text, model_name=None)
    except Exception as e:
        logger.warning(f"Error counting tokens from messages: {e}")
        return None


def safe_add(
    current: Optional[Union[int, float]],
    value: Optional[Union[int, float]],
) -> Optional[Union[int, float]]:
    """
    NULL-safe addition for numeric values (token counts or costs).

    Returns None if both values are None.
    Returns the sum if at least one value is not None (treating None as 0).

    Args:
        current: Current accumulated value (or None)
        value: Value to add (or None)

    Returns:
        Sum of values, or None if both inputs are None

    Examples:
        safe_add(None, None) -> None
        safe_add(100, None) -> 100
        safe_add(None, 50) -> 50
        safe_add(100, 50) -> 150
        safe_add(1.5, None) -> 1.5
        safe_add(None, 0.75) -> 0.75
        safe_add(1.5, 0.75) -> 2.25
    """
    if current is None and value is None:
        return None
    return (current or 0) + (value or 0)
