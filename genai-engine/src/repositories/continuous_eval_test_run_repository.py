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
from sqlalchemy.orm import Session

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.continuous_eval_test_run_models import DatabaseContinuousEvalTestRun
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseTraceMetadata
from schemas.enums import TestRunStatus
from schemas.internal_schemas import AgenticAnnotation, ContinuousEvalTestRun
from services.continuous_eval import (
    ContinuousEvalJob,
    get_continuous_eval_queue_service,
)

logger = logging.getLogger(__name__)


class ContinuousEvalTestRunRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_test_run(
        self,
        continuous_eval_id: uuid.UUID,
        task_id: str,
        trace_ids: List[str],
    ) -> ContinuousEvalTestRun:
        """Create a test run for a continuous eval against specific traces."""
        # Validate continuous eval exists
        db_continuous_eval = (
            self.db_session.query(DatabaseContinuousEval)
            .filter(DatabaseContinuousEval.id == continuous_eval_id)
            .first()
        )
        if not db_continuous_eval:
            raise HTTPException(
                status_code=404,
                detail=f"Continuous eval {continuous_eval_id} not found.",
            )

        if db_continuous_eval.task_id != task_id:
            raise HTTPException(
                status_code=400,
                detail=f"Continuous eval {continuous_eval_id} does not belong to task {task_id}.",
            )

        # Validate all trace IDs exist
        existing_traces = (
            self.db_session.query(DatabaseTraceMetadata.trace_id)
            .filter(DatabaseTraceMetadata.trace_id.in_(trace_ids))
            .all()
        )
        existing_trace_ids = {t.trace_id for t in existing_traces}
        missing_trace_ids = set(trace_ids) - existing_trace_ids
        if missing_trace_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Traces not found: {', '.join(sorted(missing_trace_ids))}",
            )

        # Deduplicate trace IDs
        unique_trace_ids = list(dict.fromkeys(trace_ids))

        # Create test run
        now = datetime.now()
        db_test_run = DatabaseContinuousEvalTestRun(
            id=uuid.uuid4(),
            continuous_eval_id=continuous_eval_id,
            task_id=task_id,
            status=TestRunStatus.RUNNING,
            total_count=len(unique_trace_ids),
            completed_count=0,
            passed_count=0,
            failed_count=0,
            error_count=0,
            skipped_count=0,
            created_at=now,
            updated_at=now,
        )
        self.db_session.add(db_test_run)
        self.db_session.flush()

        # Create pending annotations
        queue_service = get_continuous_eval_queue_service()
        if not queue_service:
            raise HTTPException(
                status_code=503,
                detail="Continuous eval queue service is not available.",
            )

        annotations = []
        for trace_id in unique_trace_ids:
            annotation = DatabaseAgenticAnnotation(
                id=uuid.uuid4(),
                annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
                trace_id=trace_id,
                continuous_eval_id=continuous_eval_id,
                run_status=ContinuousEvalRunStatus.PENDING,
                test_run_id=db_test_run.id,
                created_at=now,
                updated_at=now,
            )
            self.db_session.add(annotation)
            annotations.append(annotation)

        # Commit all annotations so worker threads can see them
        self.db_session.commit()

        # Now enqueue jobs — annotations are visible to workers
        for annotation in annotations:
            job = ContinuousEvalJob(
                annotation_id=annotation.id,
                trace_id=annotation.trace_id,
                continuous_eval_id=continuous_eval_id,
                task_id=task_id,
                delay_seconds=0,
            )
            queue_service.enqueue(job)

        logger.info(
            f"Created test run {db_test_run.id} with {len(unique_trace_ids)} traces for eval {continuous_eval_id}",
        )

        return ContinuousEvalTestRun.from_db_model(db_test_run)

    def get_test_run(
        self,
        test_run_id: uuid.UUID,
    ) -> ContinuousEvalTestRun:
        """Get a test run by ID."""
        db_test_run = (
            self.db_session.query(DatabaseContinuousEvalTestRun)
            .filter(DatabaseContinuousEvalTestRun.id == test_run_id)
            .first()
        )
        if not db_test_run:
            raise HTTPException(
                status_code=404,
                detail=f"Test run {test_run_id} not found.",
            )
        return ContinuousEvalTestRun.from_db_model(db_test_run)

    def list_test_runs(
        self,
        continuous_eval_id: uuid.UUID,
        pagination_parameters: Optional[PaginationParameters] = None,
    ) -> List[ContinuousEvalTestRun]:
        """List test runs for a continuous eval."""
        base_query = self.db_session.query(DatabaseContinuousEvalTestRun).filter(
            DatabaseContinuousEvalTestRun.continuous_eval_id == continuous_eval_id,
        )

        if pagination_parameters:
            sort_fn = (
                desc
                if pagination_parameters.sort == PaginationSortMethod.DESCENDING
                else asc
            )
            base_query = base_query.order_by(
                sort_fn(DatabaseContinuousEvalTestRun.created_at),
            )
            base_query = base_query.offset(
                pagination_parameters.page * pagination_parameters.page_size
            )
            base_query = base_query.limit(pagination_parameters.page_size)
        else:
            base_query = base_query.order_by(
                desc(DatabaseContinuousEvalTestRun.created_at),
            )

        db_test_runs = base_query.all()

        return [
            ContinuousEvalTestRun.from_db_model(db_test_run)
            for db_test_run in db_test_runs
        ]

    def get_test_run_results(
        self,
        test_run_id: uuid.UUID,
        pagination_parameters: Optional[PaginationParameters] = None,
    ) -> List[AgenticAnnotation]:
        """Get individual test case results for a test run."""
        base_query = self.db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.test_run_id == test_run_id,
        )

        if pagination_parameters:
            sort_fn = (
                desc
                if pagination_parameters.sort == PaginationSortMethod.DESCENDING
                else asc
            )
            base_query = base_query.order_by(
                sort_fn(DatabaseAgenticAnnotation.created_at),
            )
            base_query = base_query.offset(
                pagination_parameters.page * pagination_parameters.page_size
            )
            base_query = base_query.limit(pagination_parameters.page_size)

        db_annotations = base_query.all()

        return [
            AgenticAnnotation.from_db_model(db_annotation)
            for db_annotation in db_annotations
        ]

    def count_test_runs(self, continuous_eval_id: uuid.UUID) -> int:
        """Count test runs for a continuous eval."""
        return (
            self.db_session.query(DatabaseContinuousEvalTestRun)
            .filter(
                DatabaseContinuousEvalTestRun.continuous_eval_id == continuous_eval_id,
            )
            .count()
        )

    def delete_test_run(self, test_run_id: uuid.UUID) -> None:
        """Delete a test run and its associated annotations (via CASCADE)."""
        db_test_run = (
            self.db_session.query(DatabaseContinuousEvalTestRun)
            .filter(DatabaseContinuousEvalTestRun.id == test_run_id)
            .first()
        )
        if not db_test_run:
            raise HTTPException(
                status_code=404,
                detail=f"Test run {test_run_id} not found.",
            )
        self.db_session.delete(db_test_run)
        self.db_session.commit()

    def count_test_run_results(self, test_run_id: uuid.UUID) -> int:
        """Count results for a test run."""
        return (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.test_run_id == test_run_id)
            .count()
        )
