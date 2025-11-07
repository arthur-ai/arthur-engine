from datetime import datetime
from typing import Optional, Tuple

import sqlalchemy as sa
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import or_

from db_models.llm_eval_models import DatabaseLLMEval
from schemas.llm_eval_schemas import LLMEval
from schemas.request_schemas import (
    CreateEvalRequest,
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
)
from schemas.response_schemas import (
    LLMEvalsVersionListResponse,
    LLMEvalsVersionResponse,
    LLMGetAllMetadataListResponse,
    LLMGetAllMetadataResponse,
)


class LLMEvalsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _get_latest_db_eval(self, base_query: Query) -> DatabaseLLMEval:
        return (
            base_query.filter(DatabaseLLMEval.deleted_at.is_(None))
            .order_by(DatabaseLLMEval.version.desc())
            .first()
        )

    def _get_db_eval_by_version_number(
        self,
        base_query: Query,
        eval_version: str,
    ) -> DatabaseLLMEval:
        return base_query.filter(
            DatabaseLLMEval.version == int(eval_version),
        ).first()

    def _get_db_eval_by_datetime(
        self,
        base_query: Query,
        eval_version: str,
    ) -> DatabaseLLMEval:
        try:
            target_dt = datetime.fromisoformat(eval_version)
            return (
                base_query.filter(
                    sa.func.abs(
                        sa.func.extract("epoch", DatabaseLLMEval.created_at)
                        - sa.func.extract("epoch", target_dt),
                    )
                    < 1,
                )
                .order_by(DatabaseLLMEval.created_at.desc())
                .first()
            )
        except ValueError:
            raise ValueError(
                f"Invalid eval_version format '{eval_version}'. Must be 'latest', "
                f"a version number, or an ISO datetime string.",
            )

    def _get_db_eval_by_version(
        self,
        base_query: Query,
        eval_version: str,
        err_message: str = "LLM eval version not found",
    ) -> DatabaseLLMEval:
        db_eval = None

        if eval_version == "latest":
            db_eval = self._get_latest_db_eval(base_query)
        elif eval_version.isdigit():
            db_eval = self._get_db_eval_by_version_number(
                base_query,
                eval_version,
            )
        else:
            db_eval = self._get_db_eval_by_datetime(base_query, eval_version)

        if not db_eval:
            raise ValueError(err_message)

        return db_eval

    def _apply_sorting_pagination_and_count(
        self,
        query: Query,
        pagination_parameters: PaginationParameters,
        sort_column,
    ) -> Tuple[Query, int]:
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

        # Get total count BEFORE applying pagination
        total_count = query.count()

        # Apply pagination
        query = query.offset(
            pagination_parameters.page * pagination_parameters.page_size,
        )
        query = query.limit(pagination_parameters.page_size)

        return query, total_count

    def _apply_versions_filters_to_query(
        self,
        query: Query,
        filter_request: LLMGetVersionsFilterRequest,
    ) -> Query:
        """
        Apply filters to a query based on the filter request.

        Parameters:
            query: Query - the SQLAlchemy query to filter

        Returns:
            Query - the query with filters applied
        """
        # Filter by model provider
        if filter_request.model_provider:
            query = query.filter(
                DatabaseLLMEval.model_provider == filter_request.model_provider,
            )

        # Filter by model name using LIKE for partial matching
        if filter_request.model_name:
            query = query.filter(
                DatabaseLLMEval.model_name.like(f"%{filter_request.model_name}%"),
            )

        # Filter by start time (inclusive)
        if filter_request.created_after:
            query = query.filter(
                DatabaseLLMEval.created_at >= filter_request.created_after,
            )

        # Filter by end time (exclusive)
        if filter_request.created_before:
            query = query.filter(
                DatabaseLLMEval.created_at < filter_request.created_before,
            )

        # Filter by deleted status
        if filter_request.exclude_deleted == True:
            query = query.filter(DatabaseLLMEval.deleted_at.is_(None))

        # Filter by min version
        if filter_request.min_version is not None:
            query = query.filter(
                DatabaseLLMEval.version >= filter_request.min_version,
            )

        # Filter by max version
        if filter_request.max_version is not None:
            query = query.filter(
                DatabaseLLMEval.version <= filter_request.max_version,
            )

        return query

    def _apply_get_all_filters_to_query(
        self,
        query: Query,
        filter_request: LLMGetAllFilterRequest,
    ) -> Query:
        """
        Apply filters to a query based on the filter request.

        Parameters:
            query: Query - the SQLAlchemy query to filter

        Returns:
            Query - the query with filters applied
        """
        # Filter by prompt names using LIKE for partial matching
        if filter_request.llm_asset_names:
            name_conditions = [
                DatabaseLLMEval.name.like(f"%{name}%")
                for name in filter_request.llm_asset_names
            ]
            query = query.filter(or_(*name_conditions))

        # Filter by model provider
        if filter_request.model_provider:
            query = query.filter(
                DatabaseLLMEval.model_provider == filter_request.model_provider,
            )

        # Filter by model name using LIKE for partial matching
        if filter_request.model_name:
            query = query.filter(
                DatabaseLLMEval.model_name.like(f"%{filter_request.model_name}%"),
            )

        # Filter by start time (inclusive)
        if filter_request.created_after:
            query = query.filter(
                DatabaseLLMEval.created_at >= filter_request.created_after,
            )

        # Filter by end time (exclusive)
        if filter_request.created_before:
            query = query.filter(
                DatabaseLLMEval.created_at < filter_request.created_before,
            )

        return query

    def get_eval(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str = "latest",
    ) -> LLMEval:
        """
        Get an llm eval by task_id, name, and version

        Parameters:
            task_id: str - the id of the task
            eval_name: str - the name of the llm eval
            eval_version: str = "latest" - the version of the llm eval, defaults to 'latest'

        * Note - Supports getting an llm eval by:
            - eval_version = 'latest' -> gets the latest version
            - eval_version = <string number> (e.g. '1', '2', etc.) -> gets that version
            - eval_version = <datetime> (i.e. YYYY-MM-DDTHH:MM:SS, checks to the second) -> gets the version created at that time

        Returns:
            LLMEval - the llm eval object
        """
        base_query = self.db_session.query(DatabaseLLMEval).filter(
            DatabaseLLMEval.task_id == task_id,
            DatabaseLLMEval.name == eval_name,
        )

        # Version resolution
        err_msg = f"LLM eval '{eval_name}' (version '{eval_version}') not found for task '{task_id}'"
        db_eval = self._get_db_eval_by_version(
            base_query,
            eval_version,
            err_message=err_msg,
        )

        return LLMEval.from_db_model(db_eval)

    def get_eval_versions(
        self,
        task_id: str,
        eval_name: str,
        pagination_parameters: PaginationParameters,
        filter_request: Optional[LLMGetVersionsFilterRequest] = None,
    ) -> LLMEvalsVersionListResponse:
        """
        Get all versions of an llm eval by task_id and name, including metadata:
            - version number
            - created_at and deleted_at timestamps
            - model provider and name

        Parameters:
            task_id: str - the id of the task
            eval_name: str - the name of the llm eval
            pagination_parameters: PaginationParameters - pagination and sorting params

        Returns:
            LLMEvalsVersionListResponse - the list of version metadata objects with total count
        """
        # Build base query
        base_query = self.db_session.query(DatabaseLLMEval).filter(
            DatabaseLLMEval.task_id == task_id,
            DatabaseLLMEval.name == eval_name,
        )

        # Apply filters
        if filter_request is not None:
            base_query = self._apply_versions_filters_to_query(
                base_query,
                filter_request,
            )

        # Apply sorting, pagination, and get count
        base_query, total_count = self._apply_sorting_pagination_and_count(
            base_query,
            pagination_parameters,
            DatabaseLLMEval.version,
        )

        db_evals = base_query.all()

        # If we're past the last page, return empty list
        if not db_evals:
            return LLMEvalsVersionListResponse(versions=[], count=total_count)

        versions = []
        for db_eval in db_evals:
            versions.append(
                LLMEvalsVersionResponse(
                    version=db_eval.version,
                    created_at=db_eval.created_at,
                    deleted_at=db_eval.deleted_at,
                    model_provider=db_eval.model_provider,
                    model_name=db_eval.model_name,
                ),
            )

        return LLMEvalsVersionListResponse(versions=versions, count=total_count)

    def get_all_llm_eval_metadata(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters,
        filter_request: Optional[LLMGetAllFilterRequest] = None,
    ) -> LLMGetAllMetadataListResponse:
        """
        Get metadata for all llm evals by task_id, including:
            - name
            - number of versions
            - creation timestamps for first and latest versions
            - list of deleted version numbers

        Parameters:
            task_id: str - the id of the task
            pagination_parameters: PaginationParameters - pagination and sorting params
            filter_request: LLMGetAllFilterRequest - filter request parameters

        Returns:
            LLMGetAllMetadataListResponse - list of llm eval metadata objects with total count
        """
        # Start with aggregated query
        base_query = self.db_session.query(
            DatabaseLLMEval.name.label("name"),
            sa.func.count(DatabaseLLMEval.version).label("versions"),
            sa.func.min(DatabaseLLMEval.created_at).label("created_at"),
            sa.func.max(DatabaseLLMEval.created_at).label(
                "latest_version_created_at",
            ),
        ).filter(DatabaseLLMEval.task_id == task_id)

        # Apply filters BEFORE grouping
        if filter_request is not None:
            base_query = self._apply_get_all_filters_to_query(
                base_query,
                filter_request,
            )

        # Apply grouping
        base_query = base_query.group_by(DatabaseLLMEval.name)

        # Apply sorting, pagination, and get count
        base_query, total_count = self._apply_sorting_pagination_and_count(
            base_query,
            pagination_parameters,
            DatabaseLLMEval.name,
        )

        results = base_query.all()

        if not results:
            return LLMGetAllMetadataListResponse(
                llm_metadata=[],
                count=total_count,
            )

        llm_metadata = []
        for row in results:
            # get the deleted versions
            deleted_versions = (
                self.db_session.query(DatabaseLLMEval.version)
                .filter(
                    DatabaseLLMEval.task_id == task_id,
                    DatabaseLLMEval.name == row.name,
                    DatabaseLLMEval.deleted_at.isnot(None),
                )
                .order_by(DatabaseLLMEval.version.asc())
                .all()
            )
            deleted_versions = [v for (v,) in deleted_versions]

            # set the metadata
            llm_metadata.append(
                LLMGetAllMetadataResponse(
                    name=row.name,
                    versions=row.versions,
                    created_at=row.created_at,
                    latest_version_created_at=row.latest_version_created_at,
                    deleted_versions=deleted_versions,
                ),
            )

        return LLMGetAllMetadataListResponse(
            llm_metadata=llm_metadata,
            count=total_count,
        )

    def save_eval(
        self,
        task_id: str,
        eval_name: str,
        eval_config: CreateEvalRequest,
    ) -> LLMEval:
        """
        Save an LLMEval to the database.
        If an eval with the same name exists, increment version.
        Otherwise, start at version 1.
        """
        llm_eval = LLMEval(name=eval_name, **eval_config.model_dump())

        # Check for existing versions of this eval
        latest_version = (
            self.db_session.query(sa.func.max(DatabaseLLMEval.version))
            .filter(
                DatabaseLLMEval.task_id == task_id,
                DatabaseLLMEval.name == llm_eval.name,
            )
            .scalar()
        )

        # Assign version
        llm_eval.version = (latest_version + 1) if latest_version else 1

        db_eval = llm_eval.to_db_model(task_id)

        try:
            self.db_session.add(db_eval)
            self.db_session.commit()
            self.db_session.refresh(db_eval)
            return LLMEval.from_db_model(db_eval)
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Failed to save llm eval '{llm_eval.name}' for task '{task_id}' — possible duplicate constraint.",
            )

    def soft_delete_eval_version(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
    ) -> bool:
        """
        Soft delete a specific version of an llm eval by task_id, name and version. This will delete all the data associated with
        that llm eval version except for task_id, name, created_at, deleted_at and version.

        Parameters:
            task_id: str - the id of the task
            eval_name: str - the name of the llm eval
            eval_version: str - the version of the llm eval

        * Note - Supports:
            - eval_version='latest' -> marks latest version as deleted
            - eval_version=<string number> (e.g. '1', '2', etc.) -> marks that version as deleted
            - eval_version=<datetime> (YYYY-MM-DDTHH:MM:SS, checks to the second) -> marks version created at that time
        """
        base_query = self.db_session.query(DatabaseLLMEval).filter(
            DatabaseLLMEval.task_id == task_id,
            DatabaseLLMEval.name == eval_name,
        )

        err_msg = f"llm eval '{eval_name}' not found for task '{task_id}'"
        db_eval = self._get_db_eval_by_version(
            base_query,
            eval_version,
            err_message=err_msg,
        )

        if db_eval.deleted_at is not None:
            raise ValueError(
                f"LLM eval '{eval_name}' (version {db_eval.version}) has already been deleted.",
            )

        db_eval.deleted_at = datetime.now()
        db_eval.model_name = ""
        db_eval.instructions = ""
        db_eval.min_score = 0
        db_eval.max_score = 1
        db_eval.config = None

        self.db_session.commit()

    def delete_eval(self, task_id: str, eval_name: str) -> None:
        """
        Deletes all versions of an llm eval for a given task and removes them from the database

        Parameters:
            task_id: str - the id of the task
            eval_name: str - the name of the llm eval
        """
        db_evals = (
            self.db_session.query(DatabaseLLMEval)
            .filter(
                DatabaseLLMEval.task_id == task_id,
                DatabaseLLMEval.name == eval_name,
            )
            .all()
        )

        if not db_evals:
            raise ValueError(f"LLM eval '{eval_name}' not found for task '{task_id}'")

        for db_eval in db_evals:
            self.db_session.delete(db_eval)

        self.db_session.commit()
