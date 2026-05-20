from sqlalchemy.orm import Session

from repositories.base_evaluator import BaseEvaluator
from repositories.llm_evaluator import LLMEvaluator
from repositories.ml_evals_repository import MLEvaluator
from schemas.enums import EvalType
from scorer.ml_scorers import ML_EVAL_TYPES


def get_evaluator(
    db_session: Session,
    eval_type: EvalType = EvalType.LLM_AS_A_JUDGE,
) -> BaseEvaluator:
    if eval_type in ML_EVAL_TYPES:
        return MLEvaluator(db_session)
    return LLMEvaluator(db_session)
