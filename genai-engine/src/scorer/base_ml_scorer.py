from abc import ABC, abstractmethod
from typing import Any, Dict

from schemas.response_schemas import EvalRunResponse


class BaseMLScorer(ABC):
    @abstractmethod
    def run(self, text: str, config: Dict[str, Any]) -> EvalRunResponse:
        raise NotImplementedError
