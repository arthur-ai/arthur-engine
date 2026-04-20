from abc import ABC, abstractmethod
from typing import List

from sqlalchemy.orm import Session

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
        """Return the list of variable names expected by the evaluator."""
        ...

    @abstractmethod
    def run(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
        variable_mapping: List[ContinuousEvalTransformVariableMapping],
        resolved_variables: dict[str, str],
    ) -> EvalRunResponse:
        """Execute the evaluator and return a unified response.

        Args:
            task_id: The task ID.
            eval_name: Name of the eval to run.
            eval_version: Version string (e.g. "latest" or "1").
            variable_mapping: The continuous eval variable mapping.
            resolved_variables: Variables resolved from the transform, keyed by
                eval_variable name.

        Returns:
            EvalRunResponse with score (int 0/1), reason, and cost.
        """
        ...


def get_evaluator(
    db_session: Session,
    eval_type: str = "llm_as_a_judge",
) -> "BaseEvaluator":
    """Factory: return the right evaluator for the given eval_type."""
    from repositories.ml_evals_repository import ML_EVAL_TYPES, MLEvaluator

    if eval_type in ML_EVAL_TYPES:
        return MLEvaluator(db_session)

    from repositories.llm_evaluator import LLMEvaluator

    return LLMEvaluator(db_session)
