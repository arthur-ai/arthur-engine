import uuid
from abc import ABC, abstractmethod
from typing import List

from schemas.internal_schemas import ContinuousEvalTransformVariableMapping
from schemas.response_schemas import EvalRunResponse


class BaseEvaluator(ABC):
    """Abstract base for all evaluator implementations."""

    @abstractmethod
    def get_eval_variables(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
    ) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
        variable_mapping: List[ContinuousEvalTransformVariableMapping],
        resolved_variables: dict[str, str],
        org_id: uuid.UUID,
    ) -> EvalRunResponse:
        raise NotImplementedError
