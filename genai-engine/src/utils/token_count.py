import logging
from typing import Optional, Union

import tiktoken
from pydantic import BaseModel
from tokencost import calculate_cost_by_tokens

logger = logging.getLogger(__name__)

TIKTOKEN_ENCODER = "cl100k_base"


class TokenCount(BaseModel):
    prompt_token_count: Optional[int] = None
    completion_token_count: Optional[int] = None
    total_token_count: Optional[int] = None


class TokenCost(BaseModel):
    prompt_token_cost: Optional[float] = None
    completion_token_cost: Optional[float] = None
    total_token_cost: Optional[float] = None


class TokenCountCost(BaseModel):
    token_count: Optional[TokenCount] = None
    token_cost: Optional[TokenCost] = None


class TokenCounter:
    def __init__(self, model: str = TIKTOKEN_ENCODER):
        """Initializes a titoken encoder

        :param model: tiktoken model encoder
        """
        self.encoder = tiktoken.get_encoding(model)

    def count(self, query: str):
        """returns token count of the query

        :param query: string query sent to LLM
        """
        return len(self.encoder.encode(query))


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
