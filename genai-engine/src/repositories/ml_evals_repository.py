"""MLEvalsRepository — CRUD for DatabaseMLEval.

MLEvaluator — BaseEvaluator implementation that dispatches to ML scorer wrappers.
get_ml_scorer — per-type lazy scorer initialization.
"""

import logging
from typing import List, Optional, Type

from sqlalchemy import func

from arthur_common.models.task_eval_schemas import MLEval
from sqlalchemy.orm import Session

from db_models.llm_eval_models import DatabaseMLEval, DatabaseMLEvalVersionTag, ML_EVAL_INPUT_VARIABLE
from repositories.base_evaluator import BaseEvaluator
from schemas.internal_schemas import ContinuousEvalTransformVariableMapping
from schemas.request_schemas import CreateMLEvalRequest
from schemas.response_schemas import (
    EvalRunResponse,
    MLEvalsVersionListResponse,
    MLGetAllMetadataListResponse,
    MLGetAllMetadataResponse,
    MLVersionResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-type lazy scorer registry
# ---------------------------------------------------------------------------

_ML_SCORER_REGISTRY: dict = {}


def get_ml_scorer(ml_eval_type: str):  # type: ignore[return]
    """Return (and lazily initialize) the scorer for a specific ml_eval_type.

    Each scorer is instantiated at most once, only when first requested.
    This avoids loading heavy model weights for types that are never used.
    """
    global _ML_SCORER_REGISTRY
    if ml_eval_type in _ML_SCORER_REGISTRY:
        return _ML_SCORER_REGISTRY[ml_eval_type]

    from schemas.request_schemas import (
        ML_EVAL_TYPE_PII_V1,
        ML_EVAL_TYPE_PII_V2,
        ML_EVAL_TYPE_PROMPT_INJECTION,
        ML_EVAL_TYPE_TOXICITY,
    )

    if ml_eval_type == ML_EVAL_TYPE_PII_V2:
        from scorer.ml_scorers import PIIScorerV2

        scorer = PIIScorerV2()
    elif ml_eval_type == ML_EVAL_TYPE_PII_V1:
        from scorer.ml_scorers import PIIScorerV1

        scorer = PIIScorerV1()
    elif ml_eval_type == ML_EVAL_TYPE_TOXICITY:
        from scorer.ml_scorers import ToxicityMLScorer

        scorer = ToxicityMLScorer()
    elif ml_eval_type == ML_EVAL_TYPE_PROMPT_INJECTION:
        from scorer.ml_scorers import PromptInjectionMLScorer

        scorer = PromptInjectionMLScorer()
    else:
        return None

    _ML_SCORER_REGISTRY[ml_eval_type] = scorer
    return scorer


# ---------------------------------------------------------------------------
# MLEvalsRepository
# ---------------------------------------------------------------------------


class MLEvalsRepository:
    """CRUD repository for DatabaseMLEval.

    Intentionally does NOT inherit from BaseLLMRepository to avoid the
    ChatCompletionService instantiation in that class's __init__.
    """

    db_model: Type[DatabaseMLEval] = DatabaseMLEval
    tag_db_model: Type[DatabaseMLEvalVersionTag] = DatabaseMLEvalVersionTag

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_all_tags_for_item_version(self, db_item: DatabaseMLEval) -> List[str]:
        tags = (
            self.db_session.query(self.tag_db_model.tag)
            .filter(
                self.tag_db_model.task_id == db_item.task_id,
                self.tag_db_model.name == db_item.name,
                self.tag_db_model.version == db_item.version,
            )
            .order_by(self.tag_db_model.tag.asc())
            .all()
        )
        return [t for (t,) in tags]

    def _get_base_query(self, task_id: str, name: str):  # type: ignore[return]
        return self.db_session.query(self.db_model).filter(
            self.db_model.task_id == task_id,
            self.db_model.name == name,
        )

    def _get_latest_db_item(self, task_id: str, name: str) -> Optional[DatabaseMLEval]:
        return (
            self._get_base_query(task_id, name)
            .filter(self.db_model.deleted_at.is_(None))
            .order_by(self.db_model.version.desc())
            .first()
        )

    def _get_db_item_by_version(
        self,
        task_id: str,
        name: str,
        version: str,
    ) -> Optional[DatabaseMLEval]:
        if version == "latest":
            return self._get_latest_db_item(task_id, name)
        if version.isdigit():
            return (
                self._get_base_query(task_id, name)
                .filter(self.db_model.version == int(version))
                .first()
            )
        # Try tag lookup
        return (
            self._get_base_query(task_id, name)
            .join(self.tag_db_model)
            .filter(self.tag_db_model.tag == version)
            .one_or_none()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def from_db_model(self, db_eval: DatabaseMLEval) -> MLEval:
        tags = self._get_all_tags_for_item_version(db_eval)
        return MLEval(
            name=db_eval.name,
            ml_eval_type=db_eval.ml_eval_type,
            model_provider=db_eval.model_provider,
            variables=db_eval.variables,
            tags=tags,
            config=db_eval.config,
            created_at=db_eval.created_at,
            deleted_at=db_eval.deleted_at,
            version=db_eval.version,
        )

    def save_ml_eval(
        self,
        task_id: str,
        eval_name: str,
        request: CreateMLEvalRequest,
    ) -> MLEval:
        """Create a new version of an ML eval (increments version automatically)."""
        latest = self._get_latest_db_item(task_id, eval_name)
        next_version = 1 if latest is None else (latest.version + 1)

        db_eval = DatabaseMLEval(
            task_id=task_id,
            name=eval_name,
            version=next_version,
            ml_eval_type=request.ml_eval_type,
            config=request.config,
        )
        self.db_session.add(db_eval)
        self.db_session.commit()
        self.db_session.refresh(db_eval)
        return self.from_db_model(db_eval)

    def get_ml_eval(
        self,
        task_id: str,
        eval_name: str,
        version: str = "latest",
    ) -> MLEval:
        db_eval = self._get_db_item_by_version(task_id, eval_name, version)
        if db_eval is None:
            raise ValueError(
                f"ML eval '{eval_name}' version '{version}' not found for task '{task_id}'",
            )
        return self.from_db_model(db_eval)

    def list_versions(
        self,
        task_id: str,
        eval_name: str,
    ) -> MLEvalsVersionListResponse:
        items = (
            self.db_session.query(self.db_model)
            .filter(
                self.db_model.task_id == task_id,
                self.db_model.name == eval_name,
            )
            .order_by(self.db_model.version.asc())
            .all()
        )
        versions = [
            MLVersionResponse(
                version=item.version,
                created_at=item.created_at,
                deleted_at=item.deleted_at,
                ml_eval_type=item.ml_eval_type,
                tags=self._get_all_tags_for_item_version(item),
            )
            for item in items
        ]
        return MLEvalsVersionListResponse(versions=versions, count=len(versions))

    def get_all_metadata(self, task_id: str) -> MLGetAllMetadataListResponse:
        """Return one metadata entry per distinct eval name for a task."""
        rows = (
            self.db_session.query(
                self.db_model.name,
                func.count(self.db_model.version).label("version_count"),
                func.max(self.db_model.ml_eval_type).label("ml_eval_type"),
                func.max(self.db_model.created_at).label("latest_version_created_at"),
            )
            .filter(self.db_model.task_id == task_id)
            .group_by(self.db_model.name)
            .all()
        )
        metadata = [
            MLGetAllMetadataResponse(
                name=name,
                versions=version_count,
                ml_eval_type=ml_eval_type or "",
                latest_version_created_at=latest_version_created_at,
            )
            for name, version_count, ml_eval_type, latest_version_created_at in rows
        ]
        return MLGetAllMetadataListResponse(ml_metadata=metadata, count=len(metadata))

    def delete_version(
        self,
        task_id: str,
        eval_name: str,
        version: str,
    ) -> MLEval:
        """Soft-delete a specific version."""
        from datetime import datetime

        db_eval = self._get_db_item_by_version(task_id, eval_name, version)
        if db_eval is None:
            raise ValueError(
                f"ML eval '{eval_name}' version '{version}' not found for task '{task_id}'",
            )
        db_eval.deleted_at = datetime.now()
        self.db_session.commit()
        self.db_session.refresh(db_eval)
        return self.from_db_model(db_eval)

    def delete_all_versions(
        self,
        task_id: str,
        eval_name: str,
    ) -> None:
        """Hard-delete all versions of an ML eval by name."""
        items = (
            self.db_session.query(self.db_model)
            .filter(
                self.db_model.task_id == task_id,
                self.db_model.name == eval_name,
            )
            .all()
        )
        if not items:
            raise ValueError(f"ML eval '{eval_name}' not found for task '{task_id}'")
        for item in items:
            self.db_session.delete(item)
        self.db_session.commit()


# ---------------------------------------------------------------------------
# MLEvaluator
# ---------------------------------------------------------------------------


class MLEvaluator(BaseEvaluator):
    """Runs ML-based evals using the scorer registry."""

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
                f"Cannot run this ml eval because it was deleted on: {ml_eval.deleted_at}",
            )

        text = resolved_variables.get(ML_EVAL_INPUT_VARIABLE, "")

        scorer = get_ml_scorer(ml_eval.ml_eval_type)
        if scorer is None:
            raise ValueError(
                f"No scorer registered for ml_eval_type '{ml_eval.ml_eval_type}'",
            )

        config = ml_eval.config or {}
        result = scorer.score(text=text, config=config)

        return EvalRunResponse(
            reason=result.reason,
            score=result.passed,
            cost="",
        )
