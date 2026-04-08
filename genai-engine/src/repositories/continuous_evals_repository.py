import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import (
    AgenticAnnotationType,
    ContinuousEvalRunStatus,
    PaginationSortMethod,
)
from arthur_common.models.task_eval_schemas import LLMEval
from fastapi import HTTPException
from sqlalchemy import asc, case, desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from db_models import DatabaseSpan
from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.continuous_eval_test_run_models import DatabaseContinuousEvalTestRun
from db_models.llm_eval_models import DatabaseContinuousEval
from schemas.internal_schemas import AgenticAnnotation, ContinuousEval, TraceTransform
from schemas.request_schemas import (
    ContinuousEvalCreateRequest,
    ContinuousEvalListFilterRequest,
    ContinuousEvalRunResultsListFilterRequest,
    ContinuousEvalTransformVariableMappingRequest,
    UpdateContinuousEvalRequest,
)
from schemas.response_schemas import (
    ContinuousEvalRerunResponse,
    DailyAgenticAnnotationStats,
)
from services.continuous_eval import (
    ContinuousEvalJob,
    get_continuous_eval_queue_service,
)
from utils.constants import AGENT_EXPERIMENT_SESSION_PREFIX

logger = logging.getLogger(__name__)


class ContinuousEvalsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _apply_sorting_and_pagination(
        self,
        query: Query[Any],
        pagination_parameters: PaginationParameters,
        sort_column: Any,
    ) -> Query[Any]:
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
    ) -> DatabaseContinuousEval | None:
        db_eval_transform = (
            self.db_session.query(DatabaseContinuousEval)
            .filter(DatabaseContinuousEval.id == eval_id)
            .first()
        )

        return db_eval_transform

    def validate_transform_variable_mapping(
        self,
        transform: TraceTransform,
        eval: LLMEval,
        transform_variable_mapping: List[ContinuousEvalTransformVariableMappingRequest],
    ) -> None:
        transform_vars = {v.variable_name for v in transform.definition.variables}
        eval_vars = set(eval.variables)

        # Extract the mapped variables from the mapping
        mapped_transform_vars = {
            mapping.transform_variable for mapping in transform_variable_mapping
        }
        mapped_eval_vars = {
            mapping.eval_variable for mapping in transform_variable_mapping
        }

        # Check that all transform variables in the mapping exist in the transform
        invalid_transform_vars = mapped_transform_vars - transform_vars
        if invalid_transform_vars:
            raise HTTPException(
                status_code=400,
                detail=f"Transform variables in mapping do not exist in transform: {sorted(invalid_transform_vars)}",
            )

        # Check that all eval variables in the mapping exist in the eval
        invalid_eval_vars = mapped_eval_vars - eval_vars
        if invalid_eval_vars:
            raise HTTPException(
                status_code=400,
                detail=f"Eval variables in mapping do not exist in eval: {sorted(invalid_eval_vars)}",
            )

        # Check that all eval variables are covered by the mapping
        unmapped_eval_vars = eval_vars - mapped_eval_vars
        if unmapped_eval_vars:
            raise HTTPException(
                status_code=400,
                detail=f"All eval variables must be mapped. Missing mappings for: {sorted(unmapped_eval_vars)}",
            )

    def create_continuous_eval(
        self,
        task_id: str,
        continuous_eval_request: ContinuousEvalCreateRequest,
    ) -> ContinuousEval:
        # Convert Pydantic models to dicts for JSON serialization
        transform_variable_mapping_dicts = [
            mapping.model_dump()
            for mapping in continuous_eval_request.transform_variable_mapping
        ]

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
            transform_variable_mapping=transform_variable_mapping_dicts,
            enabled=continuous_eval_request.enabled,
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
        if update_continuous_eval.llm_eval_version is not None:
            db_continuous_eval.llm_eval_version = int(
                update_continuous_eval.llm_eval_version,
            )
            has_changes = True
        if update_continuous_eval.transform_id:
            db_continuous_eval.transform_id = update_continuous_eval.transform_id
            has_changes = True
        if update_continuous_eval.transform_variable_mapping:
            # Convert Pydantic models to dicts for JSON serialization
            db_continuous_eval.transform_variable_mapping = [
                mapping.model_dump()
                for mapping in update_continuous_eval.transform_variable_mapping
            ]
            has_changes = True
        if update_continuous_eval.enabled is not None:
            db_continuous_eval.enabled = update_continuous_eval.enabled
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
        pagination_parameters: Optional[PaginationParameters] = None,
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

            if filter_request.llm_eval_name_exact:
                base_query = base_query.filter(
                    DatabaseContinuousEval.llm_eval_name
                    == filter_request.llm_eval_name_exact,
                )

            if filter_request.llm_eval_version is not None:
                base_query = base_query.filter(
                    DatabaseContinuousEval.llm_eval_version
                    == filter_request.llm_eval_version,
                )

            if filter_request.created_after:
                base_query = base_query.filter(
                    DatabaseContinuousEval.created_at >= filter_request.created_after,
                )

            if filter_request.created_before:
                base_query = base_query.filter(
                    DatabaseContinuousEval.created_at < filter_request.created_before,
                )

            if filter_request.enabled is not None:
                base_query = base_query.filter(
                    DatabaseContinuousEval.enabled == filter_request.enabled,
                )

            if filter_request.continuous_eval_ids:
                base_query = base_query.filter(
                    DatabaseContinuousEval.id.in_(filter_request.continuous_eval_ids),
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
        pagination_parameters: Optional[PaginationParameters] = None,
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
                DatabaseAgenticAnnotation.test_run_id.is_(None),
            )
        )

        if filter_request:
            if filter_request.ids:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.id.in_(filter_request.ids),
                )

            if filter_request.continuous_eval_ids:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.continuous_eval_id.in_(
                        filter_request.continuous_eval_ids,
                    ),
                )

            if filter_request.eval_name:
                base_query = base_query.filter(
                    DatabaseContinuousEval.name.ilike(
                        f"%{filter_request.eval_name}%",
                    ),
                )

            if filter_request.trace_ids:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.trace_id.in_(filter_request.trace_ids),
                )

            if filter_request.annotation_score is not None:
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

            if filter_request.continuous_eval_enabled is not None:
                base_query = base_query.filter(
                    DatabaseContinuousEval.enabled
                    == filter_request.continuous_eval_enabled,
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
                .filter(DatabaseContinuousEval.enabled == True)
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
                queue_service.enqueue(job)  # Ignore return value

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

            # if trace comes from an agent experiment, do not run evals
            if root_span.session_id is not None and root_span.session_id.startswith(
                AGENT_EXPERIMENT_SESSION_PREFIX,
            ):
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

        if annotation.continuous_eval_id is None:
            raise HTTPException(
                status_code=400,
                detail="Annotation is missing continuous_eval_id.",
            )
        continuous_eval = self.get_continuous_eval_by_id(annotation.continuous_eval_id)

        if continuous_eval.enabled is False:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot rerun this evaluation because continuous eval {continuous_eval.id} has been disabled.",
            )

        queue_service = get_continuous_eval_queue_service()
        if not queue_service:
            raise HTTPException(
                status_code=503,
                detail="Continuous eval queue service is not available.",
            )

        # If this annotation belongs to a test run, decrement the old status counter
        # and completed count so re-execution doesn't corrupt the totals
        if annotation.test_run_id is not None:
            old_status = annotation.run_status
            update_values: dict = {
                "completed_count": DatabaseContinuousEvalTestRun.completed_count - 1,
                "status": "running",
                "updated_at": datetime.now(),
            }
            if old_status == ContinuousEvalRunStatus.PASSED.value:
                update_values["passed_count"] = (
                    DatabaseContinuousEvalTestRun.passed_count - 1
                )
            elif old_status == ContinuousEvalRunStatus.FAILED.value:
                update_values["failed_count"] = (
                    DatabaseContinuousEvalTestRun.failed_count - 1
                )
            elif old_status == ContinuousEvalRunStatus.ERROR.value:
                update_values["error_count"] = (
                    DatabaseContinuousEvalTestRun.error_count - 1
                )
            elif old_status == ContinuousEvalRunStatus.SKIPPED.value:
                update_values["skipped_count"] = (
                    DatabaseContinuousEvalTestRun.skipped_count - 1
                )

            self.db_session.query(DatabaseContinuousEvalTestRun).filter(
                DatabaseContinuousEvalTestRun.id == annotation.test_run_id,
            ).update(update_values, synchronize_session=False)

        # Reset annotation to PENDING status
        annotation.run_status = ContinuousEvalRunStatus.PENDING.value
        annotation.annotation_score = None
        annotation.annotation_description = None
        annotation.input_variables = None
        annotation.cost = None
        annotation.updated_at = datetime.now()
        self.db_session.commit()

        if annotation.trace_id is None:
            raise HTTPException(
                status_code=400,
                detail="Annotation is missing trace_id.",
            )

        # Re-queue the job with no delay
        job = ContinuousEvalJob(
            annotation_id=annotation.id,
            trace_id=annotation.trace_id,
            continuous_eval_id=annotation.continuous_eval_id,
            task_id=continuous_eval.task_id,
            delay_seconds=delay_seconds,
        )
        queue_service.enqueue(job)  # Ignore return value

        return ContinuousEvalRerunResponse(run_id=run_id, trace_id=annotation.trace_id)

    def get_daily_annotation_analytics(
        self,
        task_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[DailyAgenticAnnotationStats]:
        """Get daily aggregated statistics for agentic annotations.

        Includes both continuous eval annotations and human annotations.
        """
        # Use func.date() for database-agnostic date truncation
        date_col = func.date(DatabaseAgenticAnnotation.created_at)

        # Conditional counts using CASE WHEN
        passed_count = func.count(
            case((DatabaseAgenticAnnotation.annotation_score == 1, 1)),
        )
        failed_count = func.count(
            case((DatabaseAgenticAnnotation.annotation_score == 0, 1)),
        )
        error_count = func.count(
            case((DatabaseAgenticAnnotation.run_status == "error", 1)),
        )
        skipped_count = func.count(
            case((DatabaseAgenticAnnotation.run_status == "skipped", 1)),
        )
        total_cost = func.coalesce(func.sum(DatabaseAgenticAnnotation.cost), 0.0)
        total_count = func.count(DatabaseAgenticAnnotation.id)

        # Build query with JOIN to continuous_evals for task_id filtering
        # Note: This will only include annotations with a continuous_eval_id (not human annotations)
        # If human annotations should be included, need to use LEFT JOIN and filter differently
        query = (
            self.db_session.query(
                date_col.label("date"),
                passed_count.label("passed_count"),
                failed_count.label("failed_count"),
                error_count.label("error_count"),
                skipped_count.label("skipped_count"),
                total_cost.label("total_cost"),
                total_count.label("total_count"),
            )
            .join(
                DatabaseContinuousEval,
                DatabaseAgenticAnnotation.continuous_eval_id
                == DatabaseContinuousEval.id,
            )
            .filter(
                DatabaseContinuousEval.task_id == task_id,
                DatabaseAgenticAnnotation.created_at >= start_time,
                DatabaseAgenticAnnotation.created_at < end_time,
                DatabaseAgenticAnnotation.test_run_id.is_(None),
            )
            .group_by(date_col)
            .order_by(desc(date_col))
        )

        results = query.all()

        # Convert to response model instances
        return [
            DailyAgenticAnnotationStats(
                date=str(row.date),
                passed_count=row.passed_count,
                failed_count=row.failed_count,
                error_count=row.error_count,
                skipped_count=row.skipped_count,
                total_cost=float(row.total_cost),
                total_count=row.total_count,
            )
            for row in results
        ]
