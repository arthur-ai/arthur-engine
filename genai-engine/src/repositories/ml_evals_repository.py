from typing import Any, Dict, List, Optional, Type, cast

from pydantic import BaseModel
from sqlalchemy.orm import Session

from db_models.llm_eval_models import DatabaseLLMEval, DatabaseLLMEvalVersionTag
from repositories.base_evaluator import BaseEvaluator
from repositories.base_llm_repository import BaseLLMRepository
from schemas.internal_schemas import ContinuousEvalTransformVariableMapping
from schemas.llm_eval_schemas import MLEval
from schemas.request_schemas import CreateMLEvalRequest
from schemas.response_schemas import (
    EvalRunResponse,
    MLEvalsVersionListResponse,
    MLVersionResponse,
)

# Known ML eval types stored in the shared llm_evals table.
# These are model-based evaluators that do not require an LLM-as-a-judge prompt.
ML_EVAL_TYPES = ["pii", "toxicity", "prompt_injection"]

# The single input variable every ML eval expects.
ML_EVAL_INPUT_VARIABLE = "input"

# Module-level scorer cache — scorers load heavyweight models on first use.
_ML_SCORER_REGISTRY: Dict[str, Any] = {}


def get_ml_scorer(eval_type: str) -> Optional[Any]:
    """Return a cached BaseMLScorer for the given eval_type, or None if unknown."""
    if eval_type not in ML_EVAL_TYPES:
        return None
    if eval_type not in _ML_SCORER_REGISTRY:
        if eval_type == "pii":
            from scorer.ml_scorers import PIIScorerV2

            _ML_SCORER_REGISTRY[eval_type] = PIIScorerV2()
        elif eval_type == "toxicity":
            from scorer.ml_scorers import ToxicityMLScorer

            _ML_SCORER_REGISTRY[eval_type] = ToxicityMLScorer()
        elif eval_type == "prompt_injection":
            from scorer.ml_scorers import PromptInjectionMLScorer

            _ML_SCORER_REGISTRY[eval_type] = PromptInjectionMLScorer()
    return _ML_SCORER_REGISTRY.get(eval_type)


class MLEvalsRepository(
    BaseLLMRepository[DatabaseLLMEval, DatabaseLLMEvalVersionTag, CreateMLEvalRequest],
):
    db_model: Type[DatabaseLLMEval] = DatabaseLLMEval
    tag_db_model: Type[DatabaseLLMEvalVersionTag] = DatabaseLLMEvalVersionTag
    version_list_response_model: Type[BaseModel] = MLEvalsVersionListResponse
    eval_types = ML_EVAL_TYPES

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def from_db_model(self, db_eval: DatabaseLLMEval) -> MLEval:
        tags = self._get_all_tags_for_item_version(db_eval)
        return MLEval(
            name=db_eval.name,
            eval_type=db_eval.eval_type,
            variables=db_eval.variables,
            config=db_eval.config,
            created_at=db_eval.created_at,
            deleted_at=db_eval.deleted_at,
            version=db_eval.version,
            tags=tags,
        )

    def _to_versions_reponse_item(
        self,
        db_item: DatabaseLLMEval,
        tags: Optional[List[str]] = None,
    ) -> MLVersionResponse:
        tags = self._get_all_tags_for_item_version(db_item)
        return MLVersionResponse(
            version=db_item.version,
            eval_type=db_item.eval_type,
            created_at=db_item.created_at,
            deleted_at=db_item.deleted_at,
            tags=tags,
        )

    def _clear_db_item_data(self, db_item: DatabaseLLMEval) -> None:
        db_item.config = None

    def _extract_variables_from_item(self, item: CreateMLEvalRequest) -> List[str]:
        # Every ML eval expects a single "input" variable containing the text to score.
        return [ML_EVAL_INPUT_VARIABLE]

    def save_ml_eval(
        self,
        task_id: str,
        eval_name: str,
        item: CreateMLEvalRequest,
    ) -> MLEval:
        if item.eval_type not in ML_EVAL_TYPES:
            raise ValueError(
                f"Unknown ML eval type '{item.eval_type}'. "
                f"Supported types: {ML_EVAL_TYPES}",
            )
        return cast(MLEval, super().save_llm_item(task_id, eval_name, item))

    def get_ml_eval(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str = "latest",
    ) -> MLEval:
        return cast(MLEval, super().get_llm_item(task_id, eval_name, eval_version))

    def get_ml_eval_versions(
        self,
        task_id: str,
        eval_name: str,
        pagination_parameters,
        filter_request=None,
    ) -> MLEvalsVersionListResponse:
        return cast(
            MLEvalsVersionListResponse,
            super().get_llm_item_versions(
                task_id,
                eval_name,
                pagination_parameters,
                filter_request,
            ),
        )

    def delete_version(self, task_id: str, eval_name: str, version: str) -> MLEval:
        """Soft-delete a specific version; returns the eval with deleted_at set."""
        base_query = self._build_name_query(task_id, eval_name)
        db_item = self._get_db_item_by_version(
            base_query,
            version,
            err_message=f"No matching version of '{eval_name}' found for task '{task_id}'",
        )
        actual_version_num = str(db_item.version)
        self.soft_delete_llm_item_version(task_id, eval_name, version)
        return cast(
            MLEval,
            super().get_llm_item(task_id, eval_name, actual_version_num),
        )

    def delete_all_versions(self, task_id: str, eval_name: str) -> None:
        """Hard-delete all versions of an ML eval."""
        self.delete_llm_item(task_id, eval_name)

    def list_versions(self, task_id: str, eval_name: str) -> MLEvalsVersionListResponse:
        """List all versions of an ML eval (first 100 ascending by version)."""
        from arthur_common.models.common_schemas import PaginationParameters
        from arthur_common.models.enums import PaginationSortMethod

        pagination = PaginationParameters(
            page=0,
            page_size=100,
            sort=PaginationSortMethod.ASCENDING,
        )
        return self.get_ml_eval_versions(task_id, eval_name, pagination)


class MLEvaluator(BaseEvaluator):
    """BaseEvaluator implementation for ML-type evals (pii, toxicity, prompt_injection)."""

    def __init__(self, db_session: Session) -> None:
        self._repo = MLEvalsRepository(db_session)

    def get_eval_variables(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
    ) -> List[str]:
        ml_eval = self._repo.get_ml_eval(task_id, eval_name, eval_version)
        return ml_eval.variables

    def run(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
        variable_mapping: List[ContinuousEvalTransformVariableMapping],
        resolved_variables: dict[str, str],
    ) -> EvalRunResponse:
        ml_eval = self._repo.get_ml_eval(task_id, eval_name, eval_version)

        if ml_eval.deleted_at is not None:
            raise ValueError(
                f"Cannot run eval '{eval_name}' version {ml_eval.version}: it has been deleted.",
            )

        scorer = get_ml_scorer(ml_eval.eval_type)
        if scorer is None:
            raise ValueError(
                f"No scorer registered for eval type '{ml_eval.eval_type}'. "
                f"Supported types: {ML_EVAL_TYPES}",
            )

        text = resolved_variables.get(ML_EVAL_INPUT_VARIABLE, "")
        config: dict[str, Any] = ml_eval.config or {}
        result = scorer.score(text=text, config=config)

        return EvalRunResponse(
            reason=result.reason,
            score=int(result.passed),
            cost="",
        )
