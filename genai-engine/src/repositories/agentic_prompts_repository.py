from datetime import datetime
from typing import Any, Dict, Optional

import sqlalchemy as sa
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session

from custom_types import QueryT
from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from typing import Type

from pydantic import BaseModel

from db_models.agentic_prompt_models import Base, DatabaseAgenticPrompt
from repositories.base_llm_repository import BaseLLMRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.response_schemas import (
    AgenticPromptVersionListResponse,
    AgenticPromptVersionResponse,
)


class AgenticPromptRepository(BaseLLMRepository):
    db_model: Type[Base] = DatabaseAgenticPrompt
    version_list_response_model: Type[BaseModel] = AgenticPromptVersionListResponse

    def _from_db_model(self, db_item: Base) -> BaseModel:
        return AgenticPrompt.from_db_model(db_item)

    def _to_versions_reponse_item(self, db_item: Base) -> AgenticPromptVersionResponse:
        num_messages = len(db_item.messages or [])
        num_tools = len(db_item.tools or [])

        return AgenticPromptVersionResponse(
            version=db_item.version,
            created_at=db_item.created_at,
            deleted_at=db_item.deleted_at,
            model_provider=db_item.model_provider,
            model_name=db_item.model_name,
            num_messages=num_messages,
            num_tools=num_tools,
        )

    def _clear_db_item_data(self, db_item: Base) -> None:
        db_item.model_name = ""
        db_item.messages = []
        db_item.tools = None
        db_item.config = None

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_prompt(self, **kwargs: Any) -> AgenticPrompt:
        return AgenticPrompt(**kwargs)

    def _get_latest_db_prompt(
        self,
        base_query: QueryT,
    ) -> Optional[DatabaseAgenticPrompt]:
        return (
            base_query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))
            .order_by(DatabaseAgenticPrompt.version.desc())
            .first()
        )

    def _get_db_prompt_by_version_number(
        self,
        base_query: QueryT,
        prompt_version: str,
    ) -> Optional[DatabaseAgenticPrompt]:
        return base_query.filter(
            DatabaseAgenticPrompt.version == int(prompt_version),
        ).first()

    def _get_db_prompt_by_datetime(
        self,
        base_query: QueryT,
        prompt_version: str,
    ) -> Optional[DatabaseAgenticPrompt]:
        try:
            target_dt = datetime.fromisoformat(prompt_version)
            return (
                base_query.filter(
                    sa.func.abs(
                        sa.func.extract("epoch", DatabaseAgenticPrompt.created_at)
                        - sa.func.extract("epoch", target_dt),  # type: ignore[arg-type]
                    )
                    < 1,
                )
                .order_by(DatabaseAgenticPrompt.created_at.desc())
                .first()
            )
        except ValueError:
            raise ValueError(
                f"Invalid prompt_version format '{prompt_version}'. Must be 'latest', "
                f"a version number, or an ISO datetime string.",
            )

    def _get_db_prompt_by_version(
        self,
        base_query: QueryT,
        prompt_version: str,
        err_message: str = "Prompt version not found",
    ) -> DatabaseAgenticPrompt:
        db_prompt = None

        if prompt_version == "latest":
            db_prompt = self._get_latest_db_prompt(base_query)
        elif prompt_version.isdigit():
            db_prompt = self._get_db_prompt_by_version_number(
                base_query,
                prompt_version,
            )
        else:
            db_prompt = self._get_db_prompt_by_datetime(base_query, prompt_version)

        if not db_prompt:
            raise ValueError(err_message)

        return db_prompt

    def _apply_sorting_pagination_and_count(
        self,
        query: QueryT,
        pagination_parameters: PaginationParameters,
        sort_column: InstrumentedAttribute[Any],
    ) -> tuple[QueryT, int]:
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

    def get_prompt(
        self,
        task_id: str,
        prompt_name: str,
        prompt_version: str = "latest",
    ) -> AgenticPrompt:
        """
        Get a prompt by task_id, name, and version

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt
            prompt_version: str = "latest" - the version of the prompt, defaults to 'latest'

        * Note - Supports getting a prompt by:
            - prompt_version = 'latest' -> gets the latest version
            - prompt_version = <string number> (e.g. '1', '2', etc.) -> gets that version
            - prompt_version = <datetime> (i.e. YYYY-MM-DDTHH:MM:SS, checks to the second) -> gets the version created at that time

        Returns:
            AgenticPrompt - the prompt object
        """
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
            DatabaseAgenticPrompt.name == prompt_name,
        )

        # Version resolution
        err_msg = f"Prompt '{prompt_name}' (version '{prompt_version}') not found for task '{task_id}'"
        db_prompt = self._get_db_prompt_by_version(
            base_query,
            prompt_version,
            err_message=err_msg,
        )

        return AgenticPrompt.from_db_model(db_prompt)

    def get_all_prompt_metadata(
        self,
        task_id: str,
        pagination_parameters: PaginationParameters,
        filter_request: Optional[LLMGetAllFilterRequest] = None,
    ) -> LLMGetAllMetadataListResponse:
        """
        Get metadata for all prompts by task_id, including:
            - name
            - number of versions
            - creation timestamps for first and latest versions
            - list of deleted version numbers

        Parameters:
            task_id: str - the id of the task
            pagination_parameters: PaginationParameters - pagination and sorting params
            filter_request: LLMGetAllFilterRequest - filter request parameters

        Returns:
            LLMGetAllMetadataListResponse - list of prompt metadata objects with total count
        """
        # Start with aggregated query
        base_query = self.db_session.query(
            DatabaseAgenticPrompt.name.label("name"),
            sa.func.count(DatabaseAgenticPrompt.version).label("versions"),
            sa.func.min(DatabaseAgenticPrompt.created_at).label("created_at"),
            sa.func.max(DatabaseAgenticPrompt.created_at).label(
                "latest_version_created_at",
            ),
        ).filter(DatabaseAgenticPrompt.task_id == task_id)

        # Apply filters BEFORE grouping
        if filter_request is not None:
            base_query = filter_request.apply_filters_to_query(
                base_query,
                DatabaseAgenticPrompt,
            )

        # Apply grouping
        base_query = base_query.group_by(DatabaseAgenticPrompt.name)

        # Apply sorting, pagination, and get count
        base_query, total_count = self._apply_sorting_pagination_and_count(
            base_query,
            pagination_parameters,
            DatabaseAgenticPrompt.name,
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
                self.db_session.query(DatabaseAgenticPrompt.version)
                .filter(
                    DatabaseAgenticPrompt.task_id == task_id,
                    DatabaseAgenticPrompt.name == row.name,
                    DatabaseAgenticPrompt.deleted_at.isnot(None),
                )
                .order_by(DatabaseAgenticPrompt.version.asc())
                .all()
            )
            deleted_versions_list: list[int] = [v for (v,) in deleted_versions]

            # set the metadata
            llm_metadata.append(
                LLMGetAllMetadataResponse(
                    name=row.name,
                    versions=row.versions,
                    created_at=row.created_at,
                    latest_version_created_at=row.latest_version_created_at,
                    deleted_versions=deleted_versions_list,
                ),
            )

        return LLMGetAllMetadataListResponse(
            llm_metadata=llm_metadata,
            count=total_count,
        )

    def get_prompt_versions(
        self,
        task_id: str,
        prompt_name: str,
        pagination_parameters: PaginationParameters,
        filter_request: Optional[LLMGetVersionsFilterRequest] = None,
    ) -> AgenticPromptVersionListResponse:
        """
        Get all versions of a prompt by task_id and name, including metadata:
            - version number
            - created_at and deleted_at timestamps
            - model provider and name
            - number of messages
            - number of tools

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt
            pagination_parameters: PaginationParameters - pagination and sorting params

        Returns:
            AgenticPromptVersionListResponse - the list of version metadata objects with total count
        """
        # Build base query
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
            DatabaseAgenticPrompt.name == prompt_name,
        )

        # Apply filters
        if filter_request is not None:
            base_query = filter_request.apply_filters_to_query(
                base_query,
                DatabaseAgenticPrompt,
            )

        # Apply sorting, pagination, and get count
        base_query, total_count = self._apply_sorting_pagination_and_count(
            base_query,
            pagination_parameters,
            DatabaseAgenticPrompt.version,
        )

        db_prompts: list[DatabaseAgenticPrompt] = base_query.all()

        # If we're past the last page, return empty list
        if not db_prompts:
            return AgenticPromptVersionListResponse(versions=[], count=total_count)

        versions = []
        for db_prompt in db_prompts:
            num_messages = len(db_prompt.messages or [])
            num_tools = len(db_prompt.tools or [])

            versions.append(
                AgenticPromptVersionResponse(
                    version=db_prompt.version,
                    created_at=db_prompt.created_at,
                    deleted_at=db_prompt.deleted_at,
                    model_provider=db_prompt.model_provider,
                    model_name=db_prompt.model_name,
                    num_messages=num_messages,
                    num_tools=num_tools,
                ),
            )

        return AgenticPromptVersionListResponse(versions=versions, count=total_count)

    def save_prompt(
        self,
        task_id: str,
        prompt: AgenticPrompt | Dict[str, Any],
    ) -> AgenticPrompt:
        """
        Save an AgenticPrompt to the database.
        If a prompt with the same name exists, increment version.
        Otherwise, start at version 1.
        """
        if isinstance(prompt, dict):
            prompt = self.create_prompt(**prompt)

        # Check for existing versions of this prompt
        latest_version = (
            self.db_session.query(sa.func.max(DatabaseAgenticPrompt.version))
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt.name,
            )
            .scalar()
        )

        # Assign version
        prompt.version = (latest_version + 1) if latest_version else 1

        db_prompt = prompt.to_db_model(task_id)

        try:
            self.db_session.add(db_prompt)
            self.db_session.commit()
            self.db_session.refresh(db_prompt)
            return AgenticPrompt.from_db_model(db_prompt)
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Failed to save prompt '{prompt.name}' for task '{task_id}' — possible duplicate constraint.",
            )

    def soft_delete_prompt_version(
        self,
        task_id: str,
        prompt_name: str,
        prompt_version: str,
    ) -> None:
        """
        Soft delete a specific version of a prompt by task_id, name and version. This will delete all the data associated with
        that prompt version except for task_id, name, created_at, deleted_at and version.

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt
            prompt_version: str - the version of the prompt

        * Note - Supports:
            - prompt_version='latest' -> marks latest version as deleted
            - prompt_version=<string number> (e.g. '1', '2', etc.) -> marks that version as deleted
            - prompt_version=<datetime> (YYYY-MM-DDTHH:MM:SS, checks to the second) -> marks version created at that time
        """
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
            DatabaseAgenticPrompt.name == prompt_name,
        )

        err_msg = (
            f"No matching version of prompt '{prompt_name}' found for task '{task_id}'"
        )
        db_prompt = self._get_db_prompt_by_version(
            base_query,
            prompt_version,
            err_message=err_msg,
        )

        db_prompt.deleted_at = datetime.now()
        db_prompt.model_name = ""
        db_prompt.messages = []
        db_prompt.tools = None
        db_prompt.config = None

        self.db_session.commit()

    def delete_prompt(self, task_id: str, prompt_name: str) -> None:
        """
        Deletes all versions of a prompt for a given task and removes them from the database

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt
        """
        db_prompts = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt_name,
            )
            .all()
        )

        if not db_prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found for task '{task_id}'")

        for prompt in db_prompts:
            self.db_session.delete(prompt)

        self.db_session.commit()
