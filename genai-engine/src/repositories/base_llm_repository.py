# Generic repository for LLM items using TypeVar bound to Protocols for proper type safety.

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Generic, List, Optional, Protocol, Tuple, Type, TypeVar, cast

import sqlalchemy as sa
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from pydantic import BaseModel
from sqlalchemy import asc, delete, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import exists, or_

from custom_types import QueryT
from schemas.request_schemas import LLMGetAllFilterRequest, LLMGetVersionsFilterRequest
from schemas.response_schemas import (
    LLMGetAllMetadataListResponse,
    LLMGetAllMetadataResponse,
    LLMVersionResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService


# Protocols defining the required attributes for database models
class _LLMItemProtocol(Protocol):
    """Protocol for database models with LLM item attributes."""

    task_id: Any
    name: Any
    version: Any
    created_at: Any
    deleted_at: Any
    model_provider: Any
    model_name: Any


class _TagProtocol(Protocol):
    """Protocol for database models with tag attributes."""

    task_id: Any
    name: Any
    version: Any
    tag: Any


class _LLMItemRequestProtocol(Protocol):
    """Protocol for request models that create LLM items."""

    def model_dump(
        self,
        *,
        mode: str = "python",
        include: Any = None,
        exclude: Any = None,
        context: Any = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = True,
        fallback: Any = None,
        serialize_as_any: bool = False,
    ) -> dict[str, Any]: ...


# TypeVars bound to Protocols for generic repository
DBModelT = TypeVar("DBModelT", bound=_LLMItemProtocol)
TagDBModelT = TypeVar("TagDBModelT", bound=_TagProtocol)
RequestT = TypeVar("RequestT", bound=_LLMItemRequestProtocol)


class BaseLLMRepository(ABC, Generic[DBModelT, TagDBModelT, RequestT]):
    # Subclasses must set these to their specific SQLAlchemy model types
    db_model: Type[DBModelT]
    tag_db_model: Type[TagDBModelT]
    version_list_response_model: Type[BaseModel] = BaseModel

    # Optional: restrict queries to specific eval_type values.
    # None means no filter (all eval types). Set in subclasses to scope the repo.
    eval_types: Optional[List[str]] = None

    # Optional: the eval_type value to stamp on newly created items when the
    # create request does not include an eval_type field.
    default_eval_type: Optional[str] = None

    def __init__(self, db_session: Session):
        if self.db_model is None:
            raise ValueError("Subclasses must define a db_model class attribute.")
        if self.tag_db_model is None:
            raise ValueError("Subclasses must define a tag_db_model class attribute.")
        if self.version_list_response_model is None:
            raise ValueError(
                "Subclasses must define a version_list_response_model class attribute.",
            )

        self.db_session = db_session
        self.chat_completion_service = ChatCompletionService()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _build_name_query(self, task_id: str, item_name: str) -> QueryT:
        """Base query scoped to (task_id, item_name) and optional eval_type filter."""
        query = self.db_session.query(self.db_model).filter(
            self.db_model.task_id == task_id,
            self.db_model.name == item_name,
        )
        if self.eval_types is not None:
            query = query.filter(self.db_model.eval_type.in_(self.eval_types))
        return query

    def _get_all_tags_for_item_version(self, db_item: DBModelT) -> List[str]:
        tags = (
            self.db_session.query(self.tag_db_model.tag)
            .filter(
                self.tag_db_model.task_id == db_item.task_id,
                self.tag_db_model.name == db_item.name,
                self.tag_db_model.version == db_item.version,
            )
            .order_by(self.tag_db_model.tag.asc())
            .all()
        )
        return [t for (t,) in tags]

    def _get_all_tags_for_item(self, task_id: str, item_name: str) -> List[str]:
        tags = (
            self.db_session.query(self.tag_db_model.tag)
            .filter(
                self.tag_db_model.task_id == task_id,
                self.tag_db_model.name == item_name,
            )
            .order_by(self.tag_db_model.tag.asc())
            .all()
        )
        return [t for (t,) in tags]

    @abstractmethod
    def from_db_model(self, db_item: DBModelT) -> BaseModel:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def _to_versions_reponse_item(self, db_item: DBModelT) -> LLMVersionResponse:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def _clear_db_item_data(self, db_item: DBModelT) -> None:
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def _extract_variables_from_item(self, item: RequestT) -> List[str]:
        raise NotImplementedError("Subclasses must implement this method.")

    def _get_latest_db_item(self, base_query: QueryT) -> DBModelT | None:
        return (
            base_query.filter(self.db_model.deleted_at.is_(None))
            .order_by(self.db_model.version.desc())
            .first()
        )

    def _get_db_item_by_version_number(
        self,
        base_query: QueryT,
        item_version: str,
    ) -> DBModelT | None:
        return base_query.filter(
            self.db_model.version == int(item_version),
        ).first()

    def _get_db_item_by_datetime(
        self,
        base_query: QueryT,
        item_version: str,
    ) -> DBModelT | None:
        try:
            target_dt = datetime.fromisoformat(item_version)
            start_epoch = sa.func.extract("epoch", self.db_model.created_at)
            end_epoch = sa.func.extract("epoch", sa.literal(target_dt))
            return (
                base_query.filter(
                    sa.func.abs(
                        start_epoch - end_epoch,
                    )
                    < 1,
                )
                .order_by(self.db_model.created_at.desc())
                .first()
            )
        except ValueError:
            return None

    def _get_db_item_by_tag(
        self,
        base_query: QueryT,
        item_version: str,
    ) -> Optional[DBModelT]:
        """
        Get a database item by tag.

        Parameters:
            base_query: Query - base query with task_id and name filters
            item_version: str - the tag to look up

        Returns:
            Optional[Base] - the database item if found, None otherwise
        """
        # Extract task_id and name from the base query filters
        # We need to join with the tag table to find the version
        return (
            base_query.join(self.tag_db_model)
            .filter(self.tag_db_model.tag == item_version)
            .one_or_none()
        )

    def _get_db_item_by_version(
        self,
        base_query: QueryT,
        item_version: str,
        err_message: str = "Version not found",
    ) -> DBModelT:
        db_item = None

        if item_version == "latest":
            db_item = self._get_latest_db_item(base_query)
        elif item_version.isdigit():
            db_item = self._get_db_item_by_version_number(
                base_query,
                item_version,
            )
        else:
            # Try to parse as datetime first
            db_item = self._get_db_item_by_datetime(base_query, item_version)

            # If not a valid datetime, try to get by tag
            if db_item is None:
                db_item = self._get_db_item_by_tag(base_query, item_version)

        if not db_item:
            raise ValueError(err_message)

        return db_item

    def _apply_sorting_pagination_and_count(
        self,
        query: QueryT,
        pagination_parameters: PaginationParameters,
        sort_column: str,
    ) -> Tuple[QueryT, int]:
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
        query: QueryT,
        filter_request: LLMGetVersionsFilterRequest,
    ) -> QueryT:
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
        query: QueryT,
        filter_request: LLMGetAllFilterRequest,
    ) -> QueryT:
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
                self.db_model.name.ilike(f"%{name}%")
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

        # Filter by tags - keep items that have at least one matching tag across any version
        if filter_request.tags:
            query = query.filter(
                exists().where(
                    sa.and_(
                        self.tag_db_model.name == self.db_model.name,
                        self.tag_db_model.task_id == self.db_model.task_id,
                        self.tag_db_model.tag.in_(filter_request.tags),
                    ),
                ),
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
            - item_version = <tag> (any other string) -> gets the version with that tag

        Returns:
            BaseModel - the llm item object
        """
        base_query = self._build_name_query(task_id, item_name)

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

    def get_llm_item_by_tag(
        self,
        task_id: str,
        item_name: str,
        tag: str,
    ) -> BaseModel:
        """
        Get an llm item by task_id, name, and tag

        Parameters:
            task_id: str - the id of the task
            item_name: str - the name of the llm item
            tag: str - the tag of the llm item to retrieve

        Returns:
            BaseModel - the llm item object
        """
        if tag == "":
            raise ValueError("Tag cannot be empty.")

        base_query = self._build_name_query(task_id, item_name)

        # Use the helper function to get by tag
        db_item = self._get_db_item_by_tag(base_query, tag)

        if db_item is None:
            raise ValueError(
                f"Tag '{tag}' not found for task '{task_id}' and item '{item_name}'.",
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
        base_query = self._build_name_query(task_id, item_name)

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
        ).filter(
            self.db_model.task_id == task_id,
        )

        # Apply eval_type filter so each repo subclass only sees its own types
        if self.eval_types is not None:
            base_query = base_query.filter(
                self.db_model.eval_type.in_(self.eval_types),
            )

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
            # get the deleted versions (scoped to this repo's eval_types)
            deleted_versions_query = self._build_name_query(task_id, row.name).filter(
                self.db_model.deleted_at.isnot(None),
            )
            deleted_versions = (
                self.db_session.query(self.db_model.version)
                .filter(
                    self.db_model.task_id == task_id,
                    self.db_model.name == row.name,
                    self.db_model.deleted_at.isnot(None),
                    *(
                        [self.db_model.eval_type.in_(self.eval_types)]
                        if self.eval_types is not None
                        else []
                    ),
                )
                .order_by(self.db_model.version.asc())
                .all()
            )
            deleted_versions = [v for (v,) in deleted_versions]

            tags = self._get_all_tags_for_item(task_id, row.name)

            # set the metadata
            llm_metadata.append(
                LLMGetAllMetadataResponse(
                    name=row.name,
                    versions=row.versions,
                    created_at=row.created_at,
                    latest_version_created_at=row.latest_version_created_at,
                    deleted_versions=deleted_versions,
                    tags=tags,
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
        item: RequestT,
    ) -> BaseModel:
        """
        Save an llm item to the database.
        If a llm item with the same name exists, increment version.
        Otherwise, start at version 1.
        """
        # Check for existing versions of this item (scoped to this repo's eval_types)
        version_query = self.db_session.query(
            sa.func.max(self.db_model.version),
        ).filter(
            self.db_model.task_id == task_id,
            self.db_model.name == item_name,
        )
        if self.eval_types is not None:
            version_query = version_query.filter(
                self.db_model.eval_type.in_(self.eval_types),
            )
        latest_version = version_query.scalar()

        # Assign version
        version = (latest_version + 1) if latest_version else 1
        variables = self._extract_variables_from_item(item)

        db_fields: dict[str, Any] = {
            "task_id": task_id,
            "name": item_name,
            "variables": variables,
            "version": version,
            "created_at": datetime.now(),
            **item.model_dump(mode="python", exclude_none=True),
        }

        # Stamp eval_type from the class default when the request doesn't include it
        if "eval_type" not in db_fields and self.default_eval_type is not None:
            db_fields["eval_type"] = self.default_eval_type

        db_item = cast(type, self.db_model)(**db_fields)

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

    def add_tag_to_llm_item_version(
        self,
        task_id: str,
        item_name: str,
        item_version: str,
        tag: str,
    ) -> BaseModel:
        """
        Add a tag to a specific version of an llm item.
        If the tag exists on a different version, remove it from that version
        and add it to this version.
        """
        if tag == "":
            raise ValueError("Tag cannot be empty")
        elif tag.casefold().strip() == "latest":
            raise ValueError("'latest' is a reserved tag")

        base_query = self._build_name_query(task_id, item_name)

        retrieved_db_item = self._get_db_item_by_version(
            base_query,
            item_version,
            err_message=f"'{item_name}' (version '{item_version}') not found for task '{task_id}'",
        )

        if retrieved_db_item.deleted_at is not None:
            raise ValueError(f"Cannot add tag to a deleted version of '{item_name}'")

        # Check if this tag already exists on any version for this (task_id, name) combo
        existing_tag_row = self.db_session.execute(
            select(self.tag_db_model).where(
                self.tag_db_model.task_id == task_id,
                self.tag_db_model.name == item_name,
                self.tag_db_model.tag == tag,
            ),
        ).scalar_one_or_none()

        # Case 1: Tag exists on the SAME version → do nothing
        if existing_tag_row and existing_tag_row.version == retrieved_db_item.version:
            self.db_session.refresh(retrieved_db_item)
            return self.from_db_model(retrieved_db_item)

        # Case 2: Tag exists on a DIFFERENT version → delete old row
        if existing_tag_row and existing_tag_row.version != retrieved_db_item.version:
            self.db_session.delete(existing_tag_row)
            self.db_session.commit()

        # Case 3: Add tag to this version
        new_tag = cast(type, self.tag_db_model)(
            task_id=task_id,
            name=item_name,
            version=retrieved_db_item.version,
            tag=tag,
        )
        self.db_session.add(new_tag)
        self.db_session.commit()

        # refresh so the version tags and tags relationships reload
        self.db_session.refresh(retrieved_db_item)

        return self.from_db_model(retrieved_db_item)

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
        base_query = self._build_name_query(task_id, item_name)

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

        # Delete all tags for this (task_id, name, version)
        self.db_session.execute(
            delete(self.tag_db_model).where(
                self.tag_db_model.task_id == task_id,
                self.tag_db_model.name == item_name,
                self.tag_db_model.version == db_item.version,
            ),
        )

        self.db_session.commit()

    def delete_llm_item(self, task_id: str, item_name: str) -> None:
        """
        Deletes all versions of an llm item for a given task and removes them from the database

        Parameters:
            task_id: str - the id of the task
            item_name: str - the name of the llm item
        """
        db_items = self._build_name_query(task_id, item_name).all()

        if not db_items:
            raise ValueError(f"'{item_name}' not found for task '{task_id}'")

        for item in db_items:
            self.db_session.delete(item)

        self.db_session.commit()

    def delete_llm_item_tag_from_version(
        self,
        task_id: str,
        item_name: str,
        item_version: str,
        tag: str,
    ) -> None:
        """
        Deletes a tag from an llm item for a given task and name

        Parameters:
            task_id: str - the id of the task
            item_name: str - the name of the llm item to delete the tag from
            item_version: str - the version of the llm item to delete the tag from
            tag: str - the tag to delete

        * Note - Supports:
            - item_version='latest' -> deletes a specific tag from the latest version
            - item_version=<string number> (e.g. '1', '2', etc.) -> deletes a specific tag from that version number
            - item_version=<datetime> (YYYY-MM-DDTHH:MM:SS, checks to the second) -> deletes a specific tag from the version created at that time
        """
        base_query = self._build_name_query(task_id, item_name)

        # Resolve version using the same helper used everywhere else
        db_item = self._get_db_item_by_version(
            base_query,
            item_version,
            err_message=(
                f"No matching version of '{item_name}' found for task '{task_id}'"
            ),
        )

        # Now delete the specific tag for the resolved version
        existing_tag_row = self.db_session.execute(
            select(self.tag_db_model).where(
                self.tag_db_model.task_id == task_id,
                self.tag_db_model.name == item_name,
                self.tag_db_model.version == db_item.version,
                self.tag_db_model.tag == tag,
            ),
        ).scalar_one_or_none()

        if existing_tag_row is None:
            raise ValueError(
                f"Tag '{tag}' not found for task '{task_id}', item '{item_name}' and version '{item_version}'.",
            )

        self.db_session.delete(existing_tag_row)
        self.db_session.commit()
