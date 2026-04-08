from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MLScoreResult:
    passed: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


class BaseMLScorer(ABC):
    """Clean V2 boundary for ML-based scorers.

    Implementations wrap V1 scorer internals; callers never see V1 types.
    """

    @abstractmethod
    def score(self, text: str, config: dict[str, Any]) -> MLScoreResult:
        """Score the given text and return a V2 result.

        Args:
            text: The text to evaluate.
            config: Evaluator-specific configuration (thresholds, entity lists, etc.).

        Returns:
            MLScoreResult with passed, reason, and optional details.
        """
        ...
