from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from db_models.transform_models import DatabaseTraceTransform, DatabaseTraceTransformVersion
from schemas.internal_schemas import TraceTransform, TraceTransformVersion
from schemas.request_schemas import (
    NewTraceTransformRequest,
    TraceTransformUpdateRequest,
    TransformListFilterRequest,
    TransformVersionListFilterRequest,
)


class TraceTransformRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _apply_sorting_pagination_and_count(
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

    def _get_db_transform_by_id(
        self,
        transform_id: UUID,
    ) -> DatabaseTraceTransform | None:
        db_transform = (
            self.db_session.query(DatabaseTraceTransform)
            .filter(DatabaseTraceTransform.id == transform_id)
            .one_or_none()
        )

        return db_transform

    def get_transform_by_id(self, transform_id: UUID) -> TraceTransform | None:
        db_transform = self._get_db_transform_by_id(transform_id)

        if not db_transform:
            return None

        return TraceTransform.from_db_model(db_transform)

    def get_transform_version(self, transform_id: UUID, version_number: int) -> TraceTransformVersion | None:
        db_transform_version = self.db_session.query(DatabaseTraceTransformVersion).filter(
            DatabaseTraceTransformVersion.transform_id == transform_id,
            DatabaseTraceTransformVersion.version_number == version_number,
        ).one_or_none()

        if not db_transform_version:
            return None

        return TraceTransformVersion.from_db_model(db_transform_version)

    def list_transforms(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters,
        filter_request: TransformListFilterRequest,
    ) -> List[TraceTransform]:
        base_query = self.db_session.query(DatabaseTraceTransform).filter(
            DatabaseTraceTransform.task_id == task_id,
        )

        # Apply filters
        if filter_request.name:
            base_query = base_query.filter(
                DatabaseTraceTransform.name.ilike(f"%{filter_request.name}%"),
            )
        if filter_request.created_after:
            base_query = base_query.filter(
                DatabaseTraceTransform.created_at >= filter_request.created_after,
            )
        if filter_request.created_before:
            base_query = base_query.filter(
                DatabaseTraceTransform.created_at < filter_request.created_before,
            )

        base_query = self._apply_sorting_pagination_and_count(
            base_query,
            pagination_parameters,
            "created_at",
        )

        db_transforms = base_query.all()

        transforms = []
        for db_transform in db_transforms:
            transforms.append(TraceTransform.from_db_model(db_transform))

        return transforms

    def list_transform_versions(
        self,
        transform_id: UUID,
        pagination_parameters: PaginationParameters,
        filter_request: TransformVersionListFilterRequest,
    ) -> List[TraceTransformVersion]:
        base_query = self.db_session.query(DatabaseTraceTransformVersion).filter(
            DatabaseTraceTransformVersion.transform_id == transform_id,
        )

        # Apply filters
        if filter_request.id:
            base_query = base_query.filter(
                DatabaseTraceTransformVersion.id == filter_request.id,
            )
        if filter_request.name:
            base_query = base_query.filter(
                DatabaseTraceTransformVersion.name.ilike(f"%{filter_request.name}%"),
            )
        if filter_request.version_number:
            base_query = base_query.filter(
                DatabaseTraceTransformVersion.version_number == filter_request.version_number,
            )
        if filter_request.transform_id:
            base_query = base_query.filter(
                DatabaseTraceTransformVersion.transform_id == filter_request.transform_id,
            )
        if filter_request.created_before:
            base_query = base_query.filter(
                DatabaseTraceTransform.created_at < filter_request.created_before,
            )

        base_query = self._apply_sorting_pagination_and_count(
            base_query,
            pagination_parameters,
            "created_at",
        )

        db_transforms = base_query.all()

        transforms = []
        for db_transform in db_transforms:
            transforms.append(TraceTransformVersion.from_db_model(db_transform))

        return transforms

    def create_transform(
        self,
        task_id: str,
        transform: NewTraceTransformRequest,
    ) -> TraceTransform:
        trace_transform = TraceTransform.from_request_model(task_id, transform)
        db_transform = trace_transform.to_db_model()
        db_transform.latest_version_number = 1
        
        transform_version = TraceTransformVersion(
            id=uuid4(),
            transform_id=db_transform.id,
            version_number=db_transform.latest_version_number,
            created_at=db_transform.created_at,
            definition=transform.definition,
        )
        db_transform_version = transform_version.to_db_model()

        try:
            # Save the transform and its version
            self.db_session.add(db_transform)
            self.db_session.add(db_transform_version)
            
            self.db_session.commit()

            self.db_session.refresh(db_transform)
            self.db_session.refresh(db_transform_version)
        except IntegrityError:
            self.db_session.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Failed to create transform due to database constraint violation",
                headers={"full_stacktrace": "false"},
            )

        return TraceTransform.from_db_model(db_transform)

    def update_transform(
        self,
        transform_id: UUID,
        transform: TraceTransformUpdateRequest,
    ) -> TraceTransform:
        db_transform = self._get_db_transform_by_id(transform_id)

        if not db_transform:
            raise HTTPException(
                status_code=404,
                detail=f"Transform {transform_id} not found",
            )

        updated_transform = False
        current_time = datetime.now()
        
        # update the metadata fields
        if transform.name is not None:
            db_transform.name = transform.name
            updated_transform = True
        if transform.description is not None:
            db_transform.description = transform.description
            updated_transform = True
        if transform.definition is not None:
            next_version_number = db_transform.latest_version_number + 1

            transform_version = TraceTransformVersion(
                id=uuid4(),
                transform_id=db_transform.id,
                version_number=next_version_number,
                created_at=current_time,
                definition=transform.definition,
            )
            db_transform_version = transform_version.to_db_model()
            db_transform.latest_version_number = next_version_number
            
            self.db_session.add(db_transform_version)
            updated_transform = True

        if updated_transform:
            db_transform.updated_at = current_time
            self.db_session.commit()
            self.db_session.refresh(db_transform)

        return TraceTransform.from_db_model(db_transform)

    def delete_transform(self, transform_id: UUID) -> None:
        db_transform = self._get_db_transform_by_id(transform_id)

        if not db_transform:
            raise HTTPException(
                status_code=404,
                detail=f"Transform {transform_id} not found",
            )

        self.db_session.delete(db_transform)
        self.db_session.commit()
