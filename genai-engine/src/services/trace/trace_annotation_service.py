import uuid
from datetime import datetime
from typing import List

from arthur_common.models.response_schemas import (
    AgenticAnnotationResponse,
    TraceResponse,
)
from sqlalchemy.orm import Session

from db_models.telemetry_models import DatabaseAgenticAnnotation, DatabaseTraceMetadata
from schemas.internal_schemas import AgenticAnnotation, TraceMetadata
from schemas.request_schemas import AgenticAnnotationRequest


class TraceAnnotationService:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    #########################################################
    # Annotation operations on trace id
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

    def get_annotation_by_trace_id(self, trace_id: str) -> AgenticAnnotation:
        return (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.trace_id == trace_id)
            .one_or_none()
        )

        if db_annotation is None:
            raise ValueError(f"Annotation for trace {trace_id} not found")

        return AgenticAnnotation.from_db_model(db_annotation)

    def delete_annotation_by_trace_id(self, trace_id: str) -> None:
        db_annotation = (
            self.db_session.query(DatabaseAgenticAnnotation)
            .filter(DatabaseAgenticAnnotation.trace_id == trace_id)
            .one_or_none()
        )

        if db_annotation is None:
            raise ValueError(f"Annotation for trace {trace_id} not found")

        self.db_session.delete(db_annotation)
        self.db_session.commit()

    def append_annotation_info_to_trace_metadata(
        self,
        trace_metadata_list: List[TraceMetadata],
    ) -> List[TraceMetadata]:
        for trace_metadata in trace_metadata_list:
            annotation = self.get_annotation_by_trace_id(trace_metadata.trace_id)
            if annotation:
                trace_metadata.annotation = AgenticAnnotation(
                    id=annotation.id,
                    trace_id=annotation.trace_id,
                    annotation_score=annotation.annotation_score,
                    annotation_description=annotation.annotation_description,
                    created_at=annotation.created_at,
                    updated_at=annotation.updated_at,
                )

        return trace_metadata_list

    def append_annotation_info_to_trace_response(
        self,
        trace_response: TraceResponse,
    ) -> TraceResponse:
        annotation = self.get_annotation_by_trace_id(trace_response.trace_id)
        if annotation:
            trace_response.annotation = AgenticAnnotationResponse(
                annotation_score=annotation.annotation_score,
                annotation_description=annotation.annotation_description,
            )

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
