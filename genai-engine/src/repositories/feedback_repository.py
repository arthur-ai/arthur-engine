import logging
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from arthur_common.models.enums import InferenceFeedbackTarget, PaginationSortMethod
from arthur_common.models.response_schemas import InferenceFeedbackResponse
from fastapi import Depends, HTTPException, status
from opentelemetry import trace
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from db_models import DatabaseInference, DatabaseInferenceFeedback, DatabaseTask
from dependencies import get_db_session
from repositories.organizations_repository import lookup_org_id
from utils.constants import SYSTEM_ORG_ID

logger = logging.getLogger()
tracer = trace.get_tracer(__name__)


class FeedbackRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_feedback(
        self,
        inference_id: str,
        target: InferenceFeedbackTarget,
        score: int,
        reason: str,
        user_id: str | None,
        org_scope: UUID | None = None,
    ) -> DatabaseInferenceFeedback:
        # Feedback is a child of the inference, so its org MUST track the
        # parent's. Derive from the inference's task — never trust the caller's
        # identity as the source of truth here.
        derived_org_id = lookup_org_id(
            self.db_session,
            select(DatabaseTask.org_id)
            .join(DatabaseInference, DatabaseInference.task_id == DatabaseTask.id)
            .where(DatabaseInference.id == inference_id),
        )
        # Tenant caller: derived org must match the caller's. Route layer
        # pre-checks this, but re-asserting here defends against future call
        # sites and the task-deleted-mid-call race that previously silently
        # stamped the fallback org.
        if org_scope is not None and derived_org_id != org_scope:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inference not found",
            )
        # Task-less inference (inference.task_id IS NULL): produced by the
        # deprecated /api/v2/validate_prompt endpoint. The INNER JOIN above
        # yields no row, so derived_org_id is None. save_prompt/save_response
        # stamp SYSTEM_ORG_ID on the rule_results for these same inferences
        # (inference_repository.save_prompt) — match that so a single
        # inference's children never split-brain across orgs. Only reachable
        # for admin callers; the tenant check above already rejected None.
        org_id = derived_org_id if derived_org_id is not None else SYSTEM_ORG_ID
        db_feedback = DatabaseInferenceFeedback(
            id=str(uuid.uuid4()),
            inference_id=inference_id,
            target=target,
            score=score,
            reason=reason,
            user_id=user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            org_id=org_id,
        )
        self.db_session.add(db_feedback)
        self.db_session.commit()

        return db_feedback

    @tracer.start_as_current_span("query_feedback")
    def query_feedback(
        self,
        sort: PaginationSortMethod | None = PaginationSortMethod.DESCENDING,
        page: int | None = 0,
        page_size: int | None = 10,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        feedback_id: str | list[str] | None = None,
        inference_id: str | list[str] | None = None,
        target: InferenceFeedbackTarget | list[InferenceFeedbackTarget] | None = None,
        score: int | list[int] | None = None,
        feedback_user_id: str | None = None,
        conversation_id: str | list[str] | None = None,
        task_id: str | list[str] | None = None,
        inference_user_id: str | None = None,
        org_scope: UUID | None = None,
    ) -> tuple[list[DatabaseInferenceFeedback], int]:
        # query for all columns of the feedback table
        stmt = self.db_session.query(DatabaseInferenceFeedback)

        # apply org-scope filter — inference_feedback has a denormalized org_id
        # so this is a single-column filter, no join required.
        if org_scope is not None:
            stmt = stmt.where(DatabaseInferenceFeedback.org_id == org_scope)

        # apply sorting
        if sort == PaginationSortMethod.DESCENDING or sort is None:
            stmt = stmt.order_by(desc(DatabaseInferenceFeedback.created_at))
        elif sort == PaginationSortMethod.ASCENDING:
            stmt = stmt.order_by(asc(DatabaseInferenceFeedback.created_at))

        # apply filters
        if start_time:
            stmt = stmt.where(DatabaseInferenceFeedback.created_at >= start_time)
        if end_time:
            stmt = stmt.where(DatabaseInferenceFeedback.created_at < end_time)
        if feedback_id:
            stmt = stmt.where(DatabaseInferenceFeedback.id.in_(feedback_id))
        if inference_id:
            stmt = stmt.where(DatabaseInferenceFeedback.inference_id.in_(inference_id))
        if target:
            stmt = stmt.where(DatabaseInferenceFeedback.target.in_(target))
        if score:
            if isinstance(score, int):
                score = [score]
            stmt = stmt.where(DatabaseInferenceFeedback.score.in_(score))
        if feedback_user_id:
            stmt = stmt.where(DatabaseInferenceFeedback.user_id.ilike(feedback_user_id))

        # apply filters that require joining the inference table
        if conversation_id or task_id or inference_user_id:
            stmt = stmt.join(
                DatabaseInference,
                DatabaseInferenceFeedback.inference_id == DatabaseInference.id,
            )
            if conversation_id:
                stmt = stmt.where(
                    DatabaseInference.conversation_id.in_(conversation_id),
                )
            if task_id:
                stmt = stmt.where(DatabaseInference.task_id.in_(task_id))
            if inference_user_id:
                stmt = stmt.where(DatabaseInference.user_id.ilike(inference_user_id))

        # calculate the count
        count = stmt.count()

        # apply pagination
        if page is not None and page_size is not None:
            stmt = stmt.offset(page * page_size)
        stmt = stmt.limit(page_size)

        # retrieve feedback results from DB
        feedback_results = stmt.all()

        return feedback_results, count


def save_feedback(
    inference_id: str,
    target: InferenceFeedbackTarget,
    score: int,
    reason: str = "",
    user_id: Optional[str] = None,
    db_session: Session = Depends(get_db_session),
    org_scope: UUID | None = None,
) -> InferenceFeedbackResponse:
    """
    Accepts feedback on a particular inference with user information and store it in the db.

    :param inference_id: The id of the inference for which feedback is being provided
    :param target: The target of the feedback
    :param score: The score of the feedback
    :param reason: Additional context provided by the user giving the reason for why they provided the given score
    :param user_id: The id of the user providing the feedback
    :param db_session: The database session

    :raises Exception: If there is an error in storing the feedback

    :return: None
    """
    try:
        feedback_repo = FeedbackRepository(db_session)
        db_feedback = feedback_repo.create_feedback(
            inference_id,
            target,
            score,
            reason,
            user_id,
            org_scope=org_scope,
        )

        return InferenceFeedbackResponse(
            id=db_feedback.id,
            inference_id=db_feedback.inference_id,
            target=db_feedback.target,
            score=db_feedback.score,
            reason=db_feedback.reason,
            user_id=db_feedback.user_id,
            created_at=db_feedback.created_at,
            updated_at=db_feedback.updated_at,
        )
    except Exception as e:
        raise e
    finally:
        db_session.close()
