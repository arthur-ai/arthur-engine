import uuid
from datetime import datetime
from typing import List, Optional

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from db_models.llm_eval_models import DatabaseContinuousEval
from schemas.internal_schemas import ContinuousEval
from schemas.request_schemas import (
    ContinuousEvalCreateRequest,
    ContinuousEvalListFilterRequest,
    UpdateContinuousEvalRequest,
)


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
