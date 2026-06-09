from sqlalchemy.orm import Session

from repositories.base_evaluator import BaseEvaluator
from repositories.llm_evaluator import LLMEvaluator
from repositories.ml_evals_repository import MLEvaluator
from schemas.enums import EvalKind


def get_evaluator(
    db_session: Session,
    eval_type: EvalKind = EvalKind.LLM_AS_A_JUDGE,
) -> BaseEvaluator:
    if eval_type != EvalKind.LLM_AS_A_JUDGE:
        return MLEvaluator(db_session)
    return LLMEvaluator(db_session)
