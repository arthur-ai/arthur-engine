from datetime import datetime
from typing import Annotated
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import InferenceFeedbackTarget
from arthur_common.models.request_schemas import FeedbackRequest
from arthur_common.models.response_schemas import (
    InferenceFeedbackResponse,
    QueryFeedbackResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette import status

from dependencies import get_db_session
from repositories.feedback_repository import FeedbackRepository, save_feedback
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import InferenceFeedback, User
from utils import constants
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

feedback_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@feedback_routes.post(
    "/feedback/{inference_id}",
    description="Post feedback for LLM Application.",
    include_in_schema=True,
    tags=["Feedback"],
    status_code=status.HTTP_201_CREATED,
    response_model=InferenceFeedbackResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.FEEDBACK_WRITE.value)
def post_feedback(
    body: FeedbackRequest,
    inference_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> InferenceFeedbackResponse:
    return save_feedback(
        str(inference_id),
        body.target,
        body.score,
        body.reason,
        body.user_id,
        db_session,
    )


@feedback_routes.get(
    "/feedback/query",
    description="Paginated feedback querying. See parameters for available filters. Includes feedback from archived tasks and rules.",
    include_in_schema=True,
    tags=["Feedback"],
    response_model=QueryFeedbackResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.FEEDBACK_READ.value)
def query_feedback(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    start_time: datetime | None = Query(
        None,
        description="Inclusive start date in ISO8601 string format",
    ),
    end_time: datetime | None = Query(
        None,
        description="Exclusive end date in ISO8601 string format",
    ),
    feedback_id: str | list[str] | None = Query(
        None,
        description="Feedback ID to filter on",
    ),
    inference_id: str | list[str] | None = Query(
        None,
        description="Inference ID to filter on",
    ),
    target: str | list[str] | None = Query(
        None,
        description=f"Target of the feedback. Must be one of {[x.value for x in InferenceFeedbackTarget]}",
    ),
    score: int | list[int] | None = Query(
        None,
        description="Score of the feedback. Must be an integer.",
    ),
    feedback_user_id: str | None = Query(
        None,
        description="User ID of the user giving feedback to filter on (query will perform fuzzy search)",
    ),
    conversation_id: str | list[str] | None = Query(
        None,
        description="Conversation ID to filter on",
    ),
    task_id: str | list[str] | None = Query(None, description="Task ID to filter on"),
    inference_user_id: str | None = Query(
        None,
        description="User ID of the user who created the inferences to filter on (query will perform fuzzy search)",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> QueryFeedbackResponse:
    try:
        # Validate the list of inference feedback targets if any exist
        valid_targets = InferenceFeedbackTarget.__members__.values()
        if (
            target is not None
            and target not in valid_targets
            and not set(target).issubset(valid_targets)
        ):
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_INVALID_INFERENCE_FEEDBACK_TARGET,
            )

        # query the DB for feedback
        feedback_repo = FeedbackRepository(db_session)
        feedback_query_result, count = feedback_repo.query_feedback(
            sort=pagination_parameters.sort,
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
            start_time=start_time,
            end_time=end_time,
            feedback_id=feedback_id,
            inference_id=inference_id,
            target=target,
            score=score,
            feedback_user_id=feedback_user_id,
            conversation_id=conversation_id,
            task_id=task_id,
            inference_user_id=inference_user_id,
        )

        # convert the feedback query results to response models
        inference_feedback_query_responses = [
            InferenceFeedback.from_database_model(f).to_response_model()
            for f in feedback_query_result
        ]

        # respond with pagination info
        return QueryFeedbackResponse(
            feedback=inference_feedback_query_responses,
            page=pagination_parameters.page,
            page_size=pagination_parameters.page_size,
            total_pages=pagination_parameters.calculate_total_pages(count),
            total_count=count,
        )
    except Exception as error:
        raise error
    finally:
        db_session.close()
