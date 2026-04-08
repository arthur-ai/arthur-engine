from abc import ABC, abstractmethod
from typing import List

from arthur_common.models.enums import EvalType
from sqlalchemy.orm import Session

from schemas.internal_schemas import ContinuousEvalTransformVariableMapping
from schemas.response_schemas import EvalRunResponse


class BaseEvaluator(ABC):
    """Abstract base for all evaluator implementations (LLM and ML)."""

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
            EvalRunResponse with score (bool), reason, and cost.
        """
        ...


def get_evaluator(eval_type: EvalType, db_session: Session) -> "BaseEvaluator":
    """Factory: return the appropriate evaluator for the given eval_type."""
    # Import here to avoid circular imports at module load time
    if eval_type == EvalType.LLM_EVAL:
        from repositories.llm_evaluator import LLMEvaluator

        return LLMEvaluator(db_session)
    elif eval_type == EvalType.ML_EVAL:
        from repositories.ml_evals_repository import MLEvaluator

        return MLEvaluator(db_session)
    else:
        raise ValueError(f"Unknown eval_type: {eval_type}")
