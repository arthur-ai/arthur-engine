from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple, Type

import sqlalchemy as sa
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from pydantic import BaseModel
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import or_

from db_models import Base
from schemas.request_schemas import LLMGetAllFilterRequest, LLMGetVersionsFilterRequest
from schemas.response_schemas import (
    LLMGetAllMetadataListResponse,
    LLMGetAllMetadataResponse,
    LLMVersionResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService


class BaseLLMRepository(ABC):
    # subclasses must set these parameters
    db_model: Type[Base] = None
    version_list_response_model: Type[BaseModel] = None

    def __init__(self, db_session: Session):
        if self.db_model is None:
            raise ValueError("Subclasses must define a db_model class attribute.")
        if self.version_list_response_model is None:
            raise ValueError(
                "Subclasses must define a version_list_response_model class attribute.",
            )

        self.db_session = db_session
        self.chat_completion_service = ChatCompletionService()

    @abstractmethod
    def from_db_model(self, db_item: Base) -> BaseModel:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def _to_versions_reponse_item(self, db_item: Base) -> LLMVersionResponse:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def _clear_db_item_data(self, db_item: Base) -> None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def _extract_variables_from_item(self, item: BaseModel) -> List[str]:
        raise NotImplementedError("Subclasses must implement this method.")

    def _get_latest_db_item(self, base_query: Query) -> Base:
        return (
            base_query.filter(self.db_model.deleted_at.is_(None))
            .order_by(self.db_model.version.desc())
            .first()
        )

    def _get_db_item_by_version_number(
        self,
        base_query: Query,
        item_version: str,
    ) -> Base:
        return base_query.filter(
            self.db_model.version == int(item_version),
        ).first()

    def _get_db_item_by_datetime(
        self,
        base_query: Query,
        item_version: str,
    ) -> Base:
        try:
            target_dt = datetime.fromisoformat(item_version)
            return (
                base_query.filter(
                    sa.func.abs(
                        sa.func.extract("epoch", self.db_model.created_at)
                        - sa.func.extract("epoch", target_dt),
                    )
                    < 1,
                )
                .order_by(self.db_model.created_at.desc())
                .first()
            )
        except ValueError:
            raise ValueError(
                f"Invalid version format '{item_version}'. Must be 'latest', "
                f"a version number, or an ISO datetime string.",
            )

    def _get_db_item_by_version(
        self,
        base_query: Query,
        item_version: str,
        err_message: str = "Version not found",
    ) -> Base:
        db_item = None

        if item_version == "latest":
            db_item = self._get_latest_db_item(base_query)
        elif item_version.isdigit():
            db_item = self._get_db_item_by_version_number(
                base_query,
                item_version,
            )
        else:
            db_item = self._get_db_item_by_datetime(base_query, item_version)

        if not db_item:
            raise ValueError(err_message)

        return db_item

    def _apply_sorting_pagination_and_count(
        self,
        query: Query,
        pagination_parameters: PaginationParameters,
        sort_column: str,
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
                self.db_model.model_provider == filter_request.model_provider,
            )

        # Filter by model name using LIKE for partial matching
        if filter_request.model_name:
            query = query.filter(
                self.db_model.model_name.like(f"%{filter_request.model_name}%"),
            )

        # Filter by start time (inclusive)
        if filter_request.created_after:
            query = query.filter(
                self.db_model.created_at >= filter_request.created_after,
            )

        # Filter by end time (exclusive)
        if filter_request.created_before:
            query = query.filter(
                self.db_model.created_at < filter_request.created_before,
            )

        # Filter by deleted status
        if filter_request.exclude_deleted == True:
            query = query.filter(self.db_model.deleted_at.is_(None))

        # Filter by min version
        if filter_request.min_version is not None:
            query = query.filter(
                self.db_model.version >= filter_request.min_version,
            )

        # Filter by max version
        if filter_request.max_version is not None:
            query = query.filter(
                self.db_model.version <= filter_request.max_version,
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
        # Filter by llm asset names using LIKE for partial matching
        if filter_request.llm_asset_names:
            name_conditions = [
                self.db_model.name.like(f"%{name}%")
                for name in filter_request.llm_asset_names
            ]
            query = query.filter(or_(*name_conditions))

        # Filter by model provider
        if filter_request.model_provider:
            query = query.filter(
                self.db_model.model_provider == filter_request.model_provider,
            )

        # Filter by model name using LIKE for partial matching
        if filter_request.model_name:
            query = query.filter(
                self.db_model.model_name.like(f"%{filter_request.model_name}%"),
            )

        # Filter by start time (inclusive)
        if filter_request.created_after:
            query = query.filter(
                self.db_model.created_at >= filter_request.created_after,
            )

        # Filter by end time (exclusive)
        if filter_request.created_before:
            query = query.filter(
                self.db_model.created_at < filter_request.created_before,
            )

        return query

    def get_llm_item(
        self,
        task_id: str,
        item_name: str,
        item_version: str = "latest",
    ) -> BaseModel:
        """
        Get an llm item by task_id, name, and version

        Parameters:
            task_id: str - the id of the task
            item_name: str - the name of the llm item
            item_version: str = "latest" - the version of the llm item, defaults to 'latest'

        * Note - Supports getting an llm item by:
            - item_version = 'latest' -> gets the latest version
            - item_version = <string number> (e.g. '1', '2', etc.) -> gets that version
            - item_version = <datetime> (i.e. YYYY-MM-DDTHH:MM:SS, checks to the second) -> gets the version created at that time

        Returns:
            BaseModel - the llm item object
        """
        base_query = self.db_session.query(self.db_model).filter(
            self.db_model.task_id == task_id,
            self.db_model.name == item_name,
        )

        # Version resolution
        err_msg = (
            f"'{item_name}' (version '{item_version}') not found for task '{task_id}'"
        )
        db_item = self._get_db_item_by_version(
            base_query,
            item_version,
            err_message=err_msg,
        )

        return self.from_db_model(db_item)

    def get_llm_item_versions(
        self,
        task_id: str,
        item_name: str,
        pagination_parameters: PaginationParameters,
        filter_request: Optional[LLMGetVersionsFilterRequest] = None,
    ) -> BaseModel:
        """
        Get all versions of an llm item by task_id and name

        Parameters:
            task_id: str - the id of the task
            item_name: str - the name of the llm item
            pagination_parameters: PaginationParameters - pagination and sorting params

        Returns:
            version_list_response_model - the list of version metadata objects with total count
        """
        # Build base query
        base_query = self.db_session.query(self.db_model).filter(
            self.db_model.task_id == task_id,
            self.db_model.name == item_name,
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
            self.db_model.version,
        )

        db_items = base_query.all()

        # If we're past the last page, return empty list
        if not db_items:
            return self.version_list_response_model(versions=[], count=total_count)

        versions = []
        for db_item in db_items:
            versions.append(self._to_versions_reponse_item(db_item))

        return self.version_list_response_model(versions=versions, count=total_count)

    def get_all_llm_item_metadata(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters,
        filter_request: Optional[LLMGetAllFilterRequest] = None,
    ) -> LLMGetAllMetadataListResponse:
        """
        Get metadata for all llm items by task_id, including:
            - name
            - number of versions
            - creation timestamps for first and latest versions
            - list of deleted version numbers

        Parameters:
            task_id: str - the id of the task
            pagination_parameters: PaginationParameters - pagination and sorting params
            filter_request: LLMGetAllFilterRequest - filter request parameters

        Returns:
            LLMGetAllMetadataListResponse - list of metadata objects with total count
        """
        # Start with aggregated query
        base_query = self.db_session.query(
            self.db_model.name.label("name"),
            sa.func.count(self.db_model.version).label("versions"),
            sa.func.min(self.db_model.created_at).label("created_at"),
            sa.func.max(self.db_model.created_at).label(
                "latest_version_created_at",
            ),
        ).filter(self.db_model.task_id == task_id)

        # Apply filters BEFORE grouping
        if filter_request is not None:
            base_query = self._apply_get_all_filters_to_query(
                base_query,
                filter_request,
            )

        # Apply grouping
        base_query = base_query.group_by(self.db_model.name)

        # Apply sorting, pagination, and get count
        base_query, total_count = self._apply_sorting_pagination_and_count(
            base_query,
            pagination_parameters,
            self.db_model.name,
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
                self.db_session.query(self.db_model.version)
                .filter(
                    self.db_model.task_id == task_id,
                    self.db_model.name == row.name,
                    self.db_model.deleted_at.isnot(None),
                )
                .order_by(self.db_model.version.asc())
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

    def save_llm_item(
        self,
        task_id: str,
        item_name: str,
        item: BaseModel,
    ) -> BaseModel:
        """
        Save an llm item to the database.
        If a llm item with the same name exists, increment version.
        Otherwise, start at version 1.
        """
        # Check for existing versions of this item
        latest_version = (
            self.db_session.query(sa.func.max(self.db_model.version))
            .filter(
                self.db_model.task_id == task_id,
                self.db_model.name == item_name,
            )
            .scalar()
        )

        # Assign version
        version = (latest_version + 1) if latest_version else 1
        variables = self._extract_variables_from_item(item)

        db_item = self.db_model(
            task_id=task_id,
            name=item_name,
            variables=variables,
            version=version,
            created_at=datetime.now(),
            **item.model_dump(mode="python", exclude_none=True),
        )

        try:
            self.db_session.add(db_item)
            self.db_session.commit()
            self.db_session.refresh(db_item)
            return self.from_db_model(db_item)
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Failed to save '{item_name}' for task '{task_id}' — possible duplicate constraint.",
            )

    def soft_delete_llm_item_version(
        self,
        task_id: str,
        item_name: str,
        item_version: str,
    ) -> None:
        """
        Soft delete a specific version of an llm item by task_id, name and version. This will delete all the data associated with
        that llm item version except for task_id, name, created_at, deleted_at and version.

        Parameters:
            task_id: str - the id of the task
            item_name: str - the name of the llm item
            item_version: str - the version of the llm item

        * Note - Supports:
            - item_version='latest' -> marks latest version as deleted
            - item_version=<string number> (e.g. '1', '2', etc.) -> marks that version as deleted
            - item_version=<datetime> (YYYY-MM-DDTHH:MM:SS, checks to the second) -> marks version created at that time
        """
        base_query = self.db_session.query(self.db_model).filter(
            self.db_model.task_id == task_id,
            self.db_model.name == item_name,
        )

        err_msg = f"No matching version of '{item_name}' found for task '{task_id}'"
        db_item = self._get_db_item_by_version(
            base_query,
            item_version,
            err_message=err_msg,
        )

        if db_item.deleted_at is not None:
            raise ValueError(
                f"'{item_name}' (version {db_item.version}) has already been deleted.",
            )

        db_item.deleted_at = datetime.now()
        self._clear_db_item_data(db_item)

        self.db_session.commit()

    def delete_llm_item(self, task_id: str, item_name: str) -> None:
        """
        Deletes all versions of an llm item for a given task and removes them from the database

        Parameters:
            task_id: str - the id of the task
            item_name: str - the name of the llm item
        """
        db_items = (
            self.db_session.query(self.db_model)
            .filter(
                self.db_model.task_id == task_id,
                self.db_model.name == item_name,
            )
            .all()
        )

        if not db_items:
            raise ValueError(f"'{item_name}' not found for task '{task_id}'")

        for item in db_items:
            self.db_session.delete(item)

        self.db_session.commit()
