import logging
import uuid
from datetime import datetime
from typing import Optional

from arthur_common.models.enums import InferenceFeedbackTarget, PaginationSortMethod
from arthur_common.models.response_schemas import InferenceFeedbackResponse
from fastapi import Depends
from opentelemetry import trace
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from db_models import DatabaseInference, DatabaseInferenceFeedback
from dependencies import get_db_session

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
    ) -> DatabaseInferenceFeedback:
        db_feedback = DatabaseInferenceFeedback(
            id=str(uuid.uuid4()),
            inference_id=inference_id,
            target=target,
            score=score,
            reason=reason,
            user_id=user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
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
    ) -> tuple[list[DatabaseInferenceFeedback], int]:
        # query for all columns of the feedback table
        stmt = self.db_session.query(DatabaseInferenceFeedback)

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
