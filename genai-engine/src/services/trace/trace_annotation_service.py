import uuid
from datetime import datetime
from typing import List, Optional

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import AgenticAnnotationType, PaginationSortMethod
from arthur_common.models.response_schemas import (
    TraceResponse,
)
from sqlalchemy import asc, desc
from sqlalchemy.orm import Query, Session

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseTraceMetadata
from schemas.internal_schemas import AgenticAnnotation, TraceMetadata
from schemas.request_schemas import (
    AgenticAnnotationListFilterRequest,
    AgenticAnnotationRequest,
)


class TraceAnnotationService:
    def __init__(self, db_session: Session) -> None:
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

    #########################################################
    # Human annotation operations on trace id
    #########################################################

    def annotate_trace(
        self,
        trace_id: str,
        annotation_request: AgenticAnnotationRequest,
    ) -> AgenticAnnotation:
        trace = (
            self.db_session.query(DatabaseTraceMetadata)
            .filter(DatabaseTraceMetadata.trace_id == trace_id)
            .one_or_none()
        )
        if trace is None:
            raise ValueError(f"Trace {trace_id} not found")

        existing_annotation = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.trace_id == trace_id)
            .filter(
                DatabaseAgenticAnnotation.annotation_type
                == AgenticAnnotationType.HUMAN.value,
            )
            .one_or_none()
        )

        if existing_annotation:
            existing_annotation.annotation_score = annotation_request.annotation_score
            existing_annotation.annotation_description = (
                annotation_request.annotation_description
            )
            existing_annotation.updated_at = datetime.now()
            db_annotation = existing_annotation
        else:
            db_annotation = DatabaseAgenticAnnotation(
                id=uuid.uuid4(),
                annotation_type=AgenticAnnotationType.HUMAN,
                trace_id=trace_id,
                annotation_score=annotation_request.annotation_score,
                annotation_description=annotation_request.annotation_description,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            self.db_session.add(db_annotation)

        self.db_session.commit()
        self.db_session.refresh(db_annotation)

        return AgenticAnnotation.from_db_model(db_annotation)

    def get_annotation_by_id(self, annotation_id: uuid.UUID) -> AgenticAnnotation:
        db_annotation = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.id == annotation_id)
            .one_or_none()
        )

        if not db_annotation:
            return None

        return AgenticAnnotation.from_db_model(db_annotation)

    def get_annotations_by_trace_id(self, trace_id: str) -> List[AgenticAnnotation]:
        db_annotations = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.trace_id == trace_id)
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
    ) -> List[AgenticAnnotation]:
        base_query = self.db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.trace_id == trace_id,
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
                DatabaseAgenticAnnotation.created_at,
            )

        db_annotations = base_query.all()
        return [
            AgenticAnnotation.from_db_model(db_annotation)
            for db_annotation in db_annotations
        ]

    def delete_annotation_by_trace_id(self, trace_id: str) -> None:
        db_annotation = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.trace_id == trace_id)
            .filter(
                DatabaseAgenticAnnotation.annotation_type
                == AgenticAnnotationType.HUMAN.value,
            )
            .one_or_none()
        )

        if db_annotation is None:
            raise ValueError(f"Annotation for trace {trace_id} not found")

        self.db_session.delete(db_annotation)
        self.db_session.commit()

    def append_annotation_info_to_trace_metadata(
        self,
        trace_metadata_list: List[TraceMetadata],
        annotation_score: Optional[int] = None,
        annotation_type: Optional[str] = None,
        continuous_eval_run_status: Optional[str] = None,
        continuous_eval_name: Optional[str] = None,
    ) -> List[TraceMetadata]:
        for trace_metadata in trace_metadata_list:
            query = self.db_session.query(DatabaseAgenticAnnotation).filter(
                DatabaseAgenticAnnotation.trace_id == trace_metadata.trace_id,
            )

            # apply filters
            if annotation_score is not None:
                query = query.filter(
                    DatabaseAgenticAnnotation.annotation_score == annotation_score,
                )
            if annotation_type is not None:
                query = query.filter(
                    DatabaseAgenticAnnotation.annotation_type == annotation_type,
                )
            if continuous_eval_run_status is not None:
                query = query.filter(
                    DatabaseAgenticAnnotation.run_status == continuous_eval_run_status,
                )
            if continuous_eval_name is not None:
                query = query.join(
                    DatabaseContinuousEval,
                    DatabaseAgenticAnnotation.continuous_eval_id
                    == DatabaseContinuousEval.id,
                ).filter(DatabaseContinuousEval.name.ilike(f"%{continuous_eval_name}%"))

            db_annotations = query.all()
            annotations = [
                AgenticAnnotation.from_db_model(db_annotation)
                for db_annotation in db_annotations
            ]

            if annotations:
                trace_metadata.annotations = annotations

        return trace_metadata_list

    def append_annotation_info_to_trace_response(
        self,
        trace_response: TraceResponse,
    ) -> TraceResponse:
        annotations = self.get_annotations_by_trace_id(trace_response.trace_id)
        if annotations:
            trace_response.annotations = [
                annotation.to_metadata_response_model() for annotation in annotations
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
