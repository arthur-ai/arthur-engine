from datetime import datetime
from typing import Any, Dict

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from schemas.agentic_prompt_schemas import (
    AgenticPrompt,
    AgenticPrompts,
)
from schemas.response_schemas import AgenticPromptNames


class AgenticPromptRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_prompt(self, **kwargs) -> AgenticPrompt:
        return AgenticPrompt(**kwargs)

    def _get_latest_db_prompt(self, base_query: Query) -> DatabaseAgenticPrompt:
        return (
            base_query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))
            .order_by(DatabaseAgenticPrompt.version.desc())
            .first()
        )

    def _get_db_prompt_by_version_number(
        self,
        base_query: Query,
        prompt_version: str,
    ) -> DatabaseAgenticPrompt:
        return base_query.filter(
            DatabaseAgenticPrompt.version == int(prompt_version),
        ).first()

    def _get_db_prompt_by_datetime(
        self,
        base_query: Query,
        prompt_version: str,
    ) -> DatabaseAgenticPrompt:
        try:
            target_dt = datetime.fromisoformat(prompt_version)
            return (
                base_query.filter(
                    sa.func.abs(
                        sa.func.extract("epoch", DatabaseAgenticPrompt.created_at)
                        - sa.func.extract("epoch", target_dt),
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
        base_query: Query,
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

    def get_all_prompts(
        self,
        task_id: str,
    ) -> AgenticPrompts:
        """
        Get all prompts by task_id, return as list of AgenticPrompt objects

        Parameters:
            task_id: str - the id of the task

        Returns:
            AgenticPrompts - the list of prompt objects
        """
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
        )

        db_prompts = base_query.all()
        prompts = [AgenticPrompt.from_db_model(db_prompt) for db_prompt in db_prompts]
        return AgenticPrompts(prompts=prompts)

    def get_prompt_versions(
        self,
        task_id: str,
        prompt_name: str,
    ) -> AgenticPrompts:
        """
        Get all versions of a prompt by task_id and name, sorted by version descending.

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt

        Returns:
            AgenticPrompts - the list of prompt objects
        """
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
            DatabaseAgenticPrompt.name == prompt_name,
        )

        db_prompts = base_query.order_by(DatabaseAgenticPrompt.version.desc()).all()

        if not db_prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found for task '{task_id}'")

        prompts = [AgenticPrompt.from_db_model(db_prompt) for db_prompt in db_prompts]
        return AgenticPrompts(prompts=prompts)

    def get_unique_prompt_names(
        self,
        task_id: str,
    ) -> AgenticPromptNames:
        """Get all unique prompt names for a given task_id."""
        base_query = self.db_session.query(DatabaseAgenticPrompt.name).filter(
            DatabaseAgenticPrompt.task_id == task_id,
        )

        prompt_names = (
            base_query.distinct().order_by(DatabaseAgenticPrompt.name.asc()).all()
        )

        if not prompt_names:
            raise ValueError(f"No prompts found for task '{task_id}'")

        names = [name for (name,) in prompt_names]
        return AgenticPromptNames(names=names)

    def save_prompt(self, task_id: str, prompt: AgenticPrompt | Dict[str, Any]) -> None:
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
    ) -> bool:
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
