import logging
from typing import Dict, Optional, Union

import tiktoken
from tokencost import calculate_cost_by_tokens

logger = logging.getLogger(__name__)

TIKTOKEN_ENCODER = "cl100k_base"


class TokenCounter:
    """Existing class - keep as is for search functionality"""

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


def compute_cost_from_counts(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Dict[str, Optional[float]]:
    """
    Compute costs from token counts using tokencost package.

    Args:
        model_name: The model name (e.g., "gpt-4", "claude-3-opus")
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens

    Returns:
        Dict with keys: prompt_cost, completion_cost, total_cost
        Values are None if computation fails.
    """
    result = {
        "prompt_cost": None,
        "completion_cost": None,
        "total_cost": None,
    }

    try:
        prompt_cost = calculate_cost_by_tokens(
            model_name=model_name,
            input_tokens=prompt_tokens,
            output_tokens=0,
        )

        completion_cost = calculate_cost_by_tokens(
            model_name=model_name,
            input_tokens=0,
            output_tokens=completion_tokens,
        )

        result["prompt_cost"] = float(prompt_cost)
        result["completion_cost"] = float(completion_cost)
        result["total_cost"] = result["prompt_cost"] + result["completion_cost"]

    except Exception as e:
        logger.warning(
            f"Error computing costs with tokencost for model {model_name}: {e}",
        )

    return result


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
