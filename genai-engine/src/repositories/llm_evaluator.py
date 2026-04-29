"""LLM Evaluator — wraps LLMEvalsRepository for the BaseEvaluator interface."""

from typing import List

from arthur_common.models.common_schemas import VariableTemplateValue
from sqlalchemy.orm import Session

from repositories.base_evaluator import BaseEvaluator
from repositories.llm_evals_repository import LLMEvalsRepository
from schemas.internal_schemas import ContinuousEvalTransformVariableMapping
from schemas.request_schemas import BaseCompletionRequest
from schemas.response_schemas import EvalRunResponse


class LLMEvaluator(BaseEvaluator):
    def __init__(self, db_session: Session) -> None:
        self._repo = LLMEvalsRepository(db_session)

    def get_eval_variables(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
    ) -> List[str]:
        llm_eval = self._repo.get_llm_item(task_id, eval_name, eval_version)
        return llm_eval.variables

    def run(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
        variable_mapping: List[ContinuousEvalTransformVariableMapping],
        resolved_variables: dict[str, str],
    ) -> EvalRunResponse:
        variables = [
            VariableTemplateValue(name=k, value=v)
            for k, v in resolved_variables.items()
        ]
        completion_request = BaseCompletionRequest(variables=variables)
        llm_result = self._repo.run_llm_eval(
            task_id=task_id,
            eval_name=eval_name,
            version=eval_version,
            completion_request=completion_request,
        )
        return EvalRunResponse(
            reason=llm_result.reason,
            score=bool(llm_result.score),
            cost=llm_result.cost,
        )
