import logging
import uuid
from datetime import datetime
from typing import List, Optional

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import (
    AgenticAnnotationType,
    ContinuousEvalRunStatus,
    PaginationSortMethod,
)
from fastapi import HTTPException
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from db_models import DatabaseSpan
from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from schemas.internal_schemas import AgenticAnnotation, ContinuousEval
from schemas.request_schemas import (
    ContinuousEvalCreateRequest,
    ContinuousEvalListFilterRequest,
    ContinuousEvalRunResultsListFilterRequest,
    UpdateContinuousEvalRequest,
)
from schemas.response_schemas import ContinuousEvalRerunResponse
from services.continuous_eval import (
    ContinuousEvalJob,
    get_continuous_eval_queue_service,
)

logger = logging.getLogger(__name__)


class ContinuousEvalsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _apply_sorting_and_pagination(
        self,
        query: Query,
        pagination_parameters: PaginationParameters,
        sort_column: str,
    ) -> Query:
        """
        Apply sorting and pagination to a query and return the total count.

        Parameters:
            query: Query - the SQLAlchemy query to sort and paginate
            pagination_parameters: PaginationParameters - pagination and sorting params
            sort_column - the column or label to sort by

        Returns:
            Tuple[Query, int] - the sorted and paginated query, and total count
        """
        # Apply sorting
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(sort_column))
        else:  # ASCENDING or default
            query = query.order_by(asc(sort_column))

        # Apply pagination
        query = query.offset(
            pagination_parameters.page * pagination_parameters.page_size,
        )
        query = query.limit(pagination_parameters.page_size)

        return query

    def _get_db_continuous_eval_by_id(
        self,
        eval_id: uuid.UUID,
    ) -> DatabaseContinuousEval:
        db_eval_transform = (
            self.db_session.query(DatabaseContinuousEval)
            .filter(DatabaseContinuousEval.id == eval_id)
            .first()
        )

        return db_eval_transform

    def create_continuous_eval(
        self,
        task_id: str,
        continuous_eval_request: ContinuousEvalCreateRequest,
    ) -> ContinuousEval:
        db_continuous_eval = DatabaseContinuousEval(
            id=uuid.uuid4(),
            name=continuous_eval_request.name,
            description=continuous_eval_request.description,
            task_id=task_id,
            llm_eval_name=continuous_eval_request.llm_eval_name,
            llm_eval_version=continuous_eval_request.llm_eval_version,
            transform_id=continuous_eval_request.transform_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        try:
            self.db_session.add(db_continuous_eval)
            self.db_session.commit()
        except IntegrityError as e:
            self.db_session.rollback()
            if "unique constraint" in str(e).lower():
                raise HTTPException(
                    status_code=400,
                    detail=f"Continuous eval with the same llm eval version and transform already exists.",
                )
            elif "foreign key constraint" in str(e).lower():
                raise HTTPException(
                    status_code=404,
                    detail=f"Attempting to create continuous eval with a non-existent llm eval or transform.",
                )
            raise

        return ContinuousEval.from_db_model(db_continuous_eval)

    def update_continuous_eval(
        self,
        eval_id: uuid.UUID,
        update_continuous_eval: UpdateContinuousEvalRequest,
    ) -> ContinuousEval:
        db_continuous_eval = self._get_db_continuous_eval_by_id(eval_id)

        if not db_continuous_eval:
            raise HTTPException(
                status_code=404,
                detail=f"Continuous eval {eval_id} not found.",
            )

        has_changes = False
        if update_continuous_eval.name:
            db_continuous_eval.name = update_continuous_eval.name
            has_changes = True
        if update_continuous_eval.description:
            db_continuous_eval.description = update_continuous_eval.description
            has_changes = True
        if update_continuous_eval.llm_eval_name:
            db_continuous_eval.llm_eval_name = update_continuous_eval.llm_eval_name
            has_changes = True
        if update_continuous_eval.llm_eval_version:
            db_continuous_eval.llm_eval_version = (
                update_continuous_eval.llm_eval_version
            )
            has_changes = True
        if update_continuous_eval.transform_id:
            db_continuous_eval.transform_id = update_continuous_eval.transform_id
            has_changes = True

        if not has_changes:
            return ContinuousEval.from_db_model(db_continuous_eval)

        db_continuous_eval.updated_at = datetime.now()
        self.db_session.commit()

        return ContinuousEval.from_db_model(db_continuous_eval)

    def get_continuous_eval_by_id(
        self,
        eval_id: uuid.UUID,
    ) -> ContinuousEval:
        db_continuous_eval = self._get_db_continuous_eval_by_id(eval_id)

        if not db_continuous_eval:
            raise HTTPException(
                status_code=404,
                detail=f"Continuous eval {eval_id} not found.",
                headers={"full_stacktrace": "false"},
            )

        return ContinuousEval.from_db_model(db_continuous_eval)

    def list_continuous_evals(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters = None,
        filter_request: Optional[ContinuousEvalListFilterRequest] = None,
    ) -> List[ContinuousEval]:
        base_query = self.db_session.query(DatabaseContinuousEval).filter(
            DatabaseContinuousEval.task_id == task_id,
        )

        if filter_request:
            if filter_request.name:
                base_query = base_query.filter(
                    DatabaseContinuousEval.name.ilike(
                        f"%{filter_request.name}%",
                    ),
                )

            if filter_request.llm_eval_name:
                base_query = base_query.filter(
                    DatabaseContinuousEval.llm_eval_name.ilike(
                        f"%{filter_request.llm_eval_name}%",
                    ),
                )

            if filter_request.created_after:
                base_query = base_query.filter(
                    DatabaseContinuousEval.created_at >= filter_request.created_after,
                )

            if filter_request.created_before:
                base_query = base_query.filter(
                    DatabaseContinuousEval.created_at < filter_request.created_before,
                )

        if pagination_parameters:
            base_query = self._apply_sorting_and_pagination(
                base_query,
                pagination_parameters,
                DatabaseContinuousEval.created_at,
            )

        db_continuous_evals = base_query.all()

        return [
            ContinuousEval.from_db_model(db_continuous_eval)
            for db_continuous_eval in db_continuous_evals
        ]

    def list_continuous_eval_run_results(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters = None,
        filter_request: Optional[ContinuousEvalRunResultsListFilterRequest] = None,
    ) -> List[AgenticAnnotation]:
        base_query = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .join(
                DatabaseContinuousEval,
                DatabaseAgenticAnnotation.continuous_eval_id
                == DatabaseContinuousEval.id,
            )
            .filter(
                DatabaseContinuousEval.task_id == task_id,
                DatabaseAgenticAnnotation.annotation_type
                == AgenticAnnotationType.CONTINUOUS_EVAL.value,
            )
        )

        if filter_request:
            if filter_request.id:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.id == filter_request.id,
                )

            if filter_request.continuous_eval_id:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.continuous_eval_id
                    == filter_request.continuous_eval_id,
                )

            if filter_request.trace_id:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.trace_id == filter_request.trace_id,
                )

            if filter_request.annotation_score:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.annotation_score
                    == filter_request.annotation_score,
                )

            if filter_request.run_status:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.run_status
                    == filter_request.run_status.value,
                )

            if filter_request.created_after:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.created_at
                    >= filter_request.created_after,
                )

            if filter_request.created_before:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.created_at
                    < filter_request.created_before,
                )

        if pagination_parameters:
            base_query = self._apply_sorting_and_pagination(
                base_query,
                pagination_parameters,
                DatabaseAgenticAnnotation.created_at,
            )

        db_agentic_annotations = base_query.all()

        return [
            AgenticAnnotation.from_db_model(db_agentic_annotation)
            for db_agentic_annotation in db_agentic_annotations
        ]

    def delete_continuous_eval(
        self,
        eval_id: uuid.UUID,
    ) -> None:
        db_continuous_eval = self._get_db_continuous_eval_by_id(
            eval_id,
        )

        if not db_continuous_eval:
            raise HTTPException(
                status_code=404,
                detail=f"Continuous eval {eval_id} not found.",
                headers={"full_stacktrace": "false"},
            )

        self.db_session.delete(db_continuous_eval)
        self.db_session.commit()

    def _enqueue_continuous_evals_for_trace(
        self,
        trace_id: str,
        task_id: str,
        delay_seconds: int = 10,
    ) -> None:
        """Enqueue continuous eval jobs for a specific trace."""
        try:
            queue_service = get_continuous_eval_queue_service()
            if not queue_service:
                logger.debug("Continuous eval queue service not available, skipping")
                return

            # Get all continuous evals for this task
            continuous_evals = (
                self.db_session.query(DatabaseContinuousEval)
                .filter(DatabaseContinuousEval.task_id == task_id)
                .all()
            )

            if not continuous_evals:
                return

            # Create pending annotations and enqueue jobs
            for continuous_eval in continuous_evals:
                annotation = DatabaseAgenticAnnotation(
                    id=uuid.uuid4(),
                    annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
                    trace_id=trace_id,
                    continuous_eval_id=continuous_eval.id,
                    run_status=ContinuousEvalRunStatus.PENDING,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                self.db_session.add(annotation)
                self.db_session.commit()
                self.db_session.refresh(annotation)

                # Enqueue job with 10s delay
                job = ContinuousEvalJob(
                    annotation_id=annotation.id,
                    trace_id=trace_id,
                    continuous_eval_id=continuous_eval.id,
                    task_id=task_id,
                    delay_seconds=delay_seconds,
                )
                queue_service.enqueue(job)

            logger.info(
                f"Enqueued {len(continuous_evals)} continuous eval jobs for trace {trace_id}",
            )
        except Exception as e:
            logger.error(
                f"Error enqueueing continuous evals for trace {trace_id}: {e}",
                exc_info=True,
            )

    def enqueue_continuous_evals_for_root_spans(
        self,
        root_spans: list[DatabaseSpan],
        delay_seconds: int = 10,
    ) -> None:
        """Find root spans and enqueue continuous eval jobs for them."""

        # Enqueue unique traces for continuous eval execution
        seen_trace_ids = set()
        for root_span in root_spans:
            if root_span.parent_span_id is not None:
                continue

            if root_span.task_id and root_span.trace_id not in seen_trace_ids:
                seen_trace_ids.add(root_span.trace_id)
                self._enqueue_continuous_evals_for_trace(
                    root_span.trace_id,
                    root_span.task_id,
                    delay_seconds=delay_seconds,
                )

    def rerun_continuous_eval_by_annotation_id(
        self,
        run_id: uuid.UUID,
        delay_seconds: int = 10,
    ) -> ContinuousEvalRerunResponse:
        """Rerun a failed continuous eval by annotation id."""
        annotation = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.id == run_id)
            .first()
        )

        if not annotation:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")

        if annotation.annotation_type != AgenticAnnotationType.CONTINUOUS_EVAL.value:
            raise HTTPException(status_code=400, detail="Run is not a continuous eval.")

        if annotation.run_status not in [
            ContinuousEvalRunStatus.FAILED.value,
            ContinuousEvalRunStatus.ERROR.value,
            ContinuousEvalRunStatus.SKIPPED.value,
        ]:
            raise HTTPException(
                status_code=400,
                detail="Cannot rerun a non-failed continuous eval.",
            )

        continuous_eval = self.get_continuous_eval_by_id(annotation.continuous_eval_id)

        queue_service = get_continuous_eval_queue_service()
        if not queue_service:
            raise HTTPException(
                status_code=503,
                detail="Continuous eval queue service is not available.",
            )

        # Reset annotation to PENDING status
        annotation.run_status = ContinuousEvalRunStatus.PENDING.value
        annotation.annotation_score = None
        annotation.annotation_description = None
        annotation.input_variables = None
        annotation.cost = None
        annotation.updated_at = datetime.now()
        self.db_session.commit()

        # Re-queue the job with no delay
        job = ContinuousEvalJob(
            annotation_id=annotation.id,
            trace_id=annotation.trace_id,
            continuous_eval_id=annotation.continuous_eval_id,
            task_id=continuous_eval.task_id,
            delay_seconds=delay_seconds,
        )
        queue_service.enqueue(job)

        return ContinuousEvalRerunResponse(run_id=run_id, trace_id=annotation.trace_id)
