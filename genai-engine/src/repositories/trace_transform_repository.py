from datetime import datetime
from typing import List
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import String, asc, cast, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from custom_types import QueryT
from db_models.agentic_experiment_models import DatabaseAgenticExperiment
from db_models.agentic_notebook_models import DatabaseAgenticNotebook
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.transform_models import DatabaseTraceTransform
from schemas.internal_schemas import TraceTransform
from schemas.request_schemas import (
    NewTraceTransformRequest,
    TraceTransformUpdateRequest,
    TransformListFilterRequest,
)
from schemas.response_schemas import TransformDependentRef, TransformDependents


class TraceTransformRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _apply_sorting_pagination_and_count(
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

    def create_transform(
        self,
        task_id: str,
        transform: NewTraceTransformRequest,
    ) -> TraceTransform:
        trace_transform = TraceTransform.from_request_model(task_id, transform)
        db_transform = trace_transform.to_db_model()

        try:
            self.db_session.add(db_transform)
            self.db_session.commit()
            self.db_session.refresh(db_transform)
        except IntegrityError:
            self.db_session.rollback()
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found.",
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
        if transform.name is not None:
            db_transform.name = transform.name
            updated_transform = True
        if transform.description is not None:
            db_transform.description = transform.description
            updated_transform = True
        if transform.definition is not None:
            db_transform.definition = transform.definition.model_dump()
            updated_transform = True

        if updated_transform:
            db_transform.updated_at = datetime.now()
            self.db_session.commit()
            self.db_session.refresh(db_transform)

        return TraceTransform.from_db_model(db_transform)

    def get_transform_dependents(self, transform_id: UUID) -> TransformDependents:
        continuous_evals = (
            self.db_session.query(
                DatabaseContinuousEval.id, DatabaseContinuousEval.name
            )
            .filter(DatabaseContinuousEval.transform_id == transform_id)
            .all()
        )

        transform_id_str = str(transform_id)

        agentic_experiments = (
            self.db_session.query(
                DatabaseAgenticExperiment.id, DatabaseAgenticExperiment.name
            )
            .filter(
                cast(DatabaseAgenticExperiment.eval_configs, String).contains(
                    transform_id_str
                )
            )
            .all()
        )

        agentic_notebooks = (
            self.db_session.query(
                DatabaseAgenticNotebook.id, DatabaseAgenticNotebook.name
            )
            .filter(
                DatabaseAgenticNotebook.eval_configs.isnot(None),
                cast(DatabaseAgenticNotebook.eval_configs, String).contains(
                    transform_id_str
                ),
            )
            .all()
        )

        return TransformDependents(
            continuous_evals=[
                TransformDependentRef(id=str(e.id), name=e.name)
                for e in continuous_evals
            ],
            agentic_experiments=[
                TransformDependentRef(id=str(e.id), name=e.name)
                for e in agentic_experiments
            ],
            agentic_notebooks=[
                TransformDependentRef(id=str(e.id), name=e.name)
                for e in agentic_notebooks
            ],
        )

    def delete_transform(self, transform_id: UUID) -> None:
        db_transform = self._get_db_transform_by_id(transform_id)

        if not db_transform:
            raise HTTPException(
                status_code=404,
                detail=f"Transform {transform_id} not found",
            )

        dependents = self.get_transform_dependents(transform_id)
        if dependents.has_dependents:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Cannot delete transform because it is referenced by other resources. "
                    "Remove these references first.",
                    "dependents": dependents.model_dump(),
                },
            )

        self.db_session.delete(db_transform)
        self.db_session.commit()
