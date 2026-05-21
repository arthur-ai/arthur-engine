import uuid
from datetime import datetime
from typing import List, Optional

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import AgenticAnnotationType, PaginationSortMethod
from arthur_common.models.response_schemas import (
    TraceResponse,
)
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from custom_types import QueryT
from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.task_models import DatabaseTask
from db_models.telemetry_models import DatabaseTraceMetadata
from repositories.organizations_repository import lookup_org_id
from schemas.internal_schemas import AgenticAnnotation
from schemas.request_schemas import (
    AgenticAnnotationListFilterRequest,
    AgenticAnnotationRequest,
)


class TraceAnnotationService:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def _apply_sorting_and_pagination(
        self,
        query: QueryT,
        pagination_parameters: PaginationParameters,
        sort_column: str,
    ) -> QueryT:
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

    #########################################################
    # Human annotation operations on trace id
    #########################################################

    def annotate_trace(
        self,
        trace_id: str,
        annotation_request: AgenticAnnotationRequest,
        org_scope: uuid.UUID | None = None,
    ) -> AgenticAnnotation:
        trace_q = self.db_session.query(DatabaseTraceMetadata).filter(
            DatabaseTraceMetadata.trace_id == trace_id,
        )
        if org_scope is not None:
            trace_q = trace_q.join(
                DatabaseTask, DatabaseTask.id == DatabaseTraceMetadata.task_id
            ).filter(DatabaseTask.org_id == str(org_scope))
        trace = trace_q.one_or_none()
        if trace is None:
            raise ValueError(f"Trace {trace_id} not found")

        existing_annotation_q = self.db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.trace_id == trace_id,
            DatabaseAgenticAnnotation.annotation_type
            == AgenticAnnotationType.HUMAN.value,
        )
        if org_scope is not None:
            existing_annotation_q = existing_annotation_q.filter(
                DatabaseAgenticAnnotation.org_id == str(org_scope),
            )
        existing_annotation = existing_annotation_q.one_or_none()

        if existing_annotation:
            existing_annotation.annotation_score = annotation_request.annotation_score
            existing_annotation.annotation_description = (
                annotation_request.annotation_description
            )
            existing_annotation.updated_at = datetime.now()
            db_annotation = existing_annotation
        else:
            task_org_id = lookup_org_id(
                self.db_session,
                select(DatabaseTask.org_id).where(DatabaseTask.id == trace.task_id),
            )
            db_annotation = DatabaseAgenticAnnotation(
                id=uuid.uuid4(),
                annotation_type=AgenticAnnotationType.HUMAN,
                trace_id=trace_id,
                annotation_score=annotation_request.annotation_score,
                annotation_description=annotation_request.annotation_description,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                org_id=task_org_id,
            )
            self.db_session.add(db_annotation)

        self.db_session.commit()
        self.db_session.refresh(db_annotation)

        return AgenticAnnotation.from_db_model(db_annotation)

    def get_annotation_by_id(
        self,
        annotation_id: uuid.UUID,
        org_scope: uuid.UUID | None = None,
    ) -> AgenticAnnotation | None:
        q = self.db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.id == annotation_id,
        )
        if org_scope is not None:
            q = q.filter(DatabaseAgenticAnnotation.org_id == str(org_scope))
        db_annotation = q.one_or_none()

        if not db_annotation:
            return None

        return AgenticAnnotation.from_db_model(db_annotation)

    def get_annotations_by_trace_id(self, trace_id: str) -> List[AgenticAnnotation]:
        db_annotations = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(
                DatabaseAgenticAnnotation.trace_id == trace_id,
                DatabaseAgenticAnnotation.test_run_id.is_(None),
            )
            .all()
        )

        return [
            AgenticAnnotation.from_db_model(db_annotation)
            for db_annotation in db_annotations
        ]

    def list_annotations_for_trace(
        self,
        trace_id: str,
        pagination_parameters: PaginationParameters,
        filter_request: Optional[AgenticAnnotationListFilterRequest] = None,
        org_scope: uuid.UUID | None = None,
    ) -> List[AgenticAnnotation]:
        base_query = self.db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.trace_id == trace_id,
            DatabaseAgenticAnnotation.test_run_id.is_(None),
        )
        if org_scope is not None:
            base_query = base_query.filter(
                DatabaseAgenticAnnotation.org_id == str(org_scope),
            )

        if filter_request:
            if filter_request.continuous_eval_id:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.continuous_eval_id
                    == filter_request.continuous_eval_id,
                )

            if filter_request.annotation_type:
                base_query = base_query.filter(
                    DatabaseAgenticAnnotation.annotation_type
                    == filter_request.annotation_type.value,
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
                DatabaseAgenticAnnotation.created_at.label("created_at").name,
            )

        db_annotations = base_query.all()
        return [
            AgenticAnnotation.from_db_model(db_annotation)
            for db_annotation in db_annotations
        ]

    def delete_annotation_by_trace_id(
        self, trace_id: str, org_scope: uuid.UUID | None = None
    ) -> None:
        q = self.db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.trace_id == trace_id,
            DatabaseAgenticAnnotation.annotation_type
            == AgenticAnnotationType.HUMAN.value,
        )
        if org_scope is not None:
            q = q.filter(DatabaseAgenticAnnotation.org_id == str(org_scope))
        db_annotation = q.one_or_none()

        if db_annotation is None:
            raise ValueError(f"Annotation for trace {trace_id} not found")

        self.db_session.delete(db_annotation)
        self.db_session.commit()

    def append_annotation_info_to_trace_response(
        self,
        trace_response: TraceResponse,
    ) -> TraceResponse:
        annotations = self.get_annotations_by_trace_id(trace_response.trace_id)
        if annotations:
            trace_response.annotations = [
                annotation.to_response_model() for annotation in annotations
            ]

        return trace_response

    def append_annotation_info_to_trace_responses(
        self,
        trace_responses: List[TraceResponse],
    ) -> List[TraceResponse]:
        for i in range(len(trace_responses)):
            trace_responses[i] = self.append_annotation_info_to_trace_response(
                trace_responses[i],
            )

        return trace_responses
