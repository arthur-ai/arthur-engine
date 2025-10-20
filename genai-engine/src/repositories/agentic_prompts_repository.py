from datetime import datetime
from typing import Any, Dict

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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

    def get_prompt(
        self,
        task_id: str,
        prompt_name: str,
        prompt_version: str = "latest",
        include_deleted: bool = False,
    ) -> AgenticPrompt:
        """
        Get a prompt by task_id, name, and version

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt
            prompt_version: str = "latest" - the version of the prompt, defaults to 'latest'
            include_deleted: bool = False - whether to include deleted prompts, defaults to False

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
        if prompt_version == "latest":
            query = base_query

            # if include_deleted is False, get the latest non-deleted prompt
            if not include_deleted:
                query = query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))

            db_prompt = query.order_by(DatabaseAgenticPrompt.version.desc()).first()
        elif prompt_version.isdigit():
            db_prompt = base_query.filter(
                DatabaseAgenticPrompt.version == int(prompt_version),
            ).first()
        else:
            try:
                target_dt = datetime.fromisoformat(prompt_version)
                db_prompt = (
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

        if not db_prompt:
            raise ValueError(
                f"Prompt '{prompt_name}' (version '{prompt_version}') not found for task '{task_id}'",
            )

        if db_prompt.deleted_at is not None and not include_deleted:
            raise ValueError(
                f"Attempting to retrieve a deleted prompt '{prompt_name}' (version '{prompt_version}').",
            )

        return AgenticPrompt.from_db_model(db_prompt)

    def get_all_prompts(
        self,
        task_id: str,
        include_deleted: bool = False,
    ) -> AgenticPrompts:
        """
        Get all prompts by task_id, return as list of AgenticPrompt objects

        Parameters:
            task_id: str - the id of the task
            include_deleted: bool = False - whether to include deleted prompts, defaults to False

        Returns:
            AgenticPrompts - the list of prompt objects
        """
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
        )

        if not include_deleted:
            base_query = base_query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))

        db_prompts = base_query.all()
        prompts = [AgenticPrompt.from_db_model(db_prompt) for db_prompt in db_prompts]
        return AgenticPrompts(prompts=prompts)

    def get_prompt_versions(
        self,
        task_id: str,
        prompt_name: str,
        include_deleted: bool = False,
    ) -> AgenticPrompts:
        """
        Get all versions of a prompt by task_id and name, sorted by version descending.

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt
            include_deleted: bool = False - whether to include deleted prompts, defaults to False

        Returns:
            AgenticPrompts - the list of prompt objects
        """
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
            DatabaseAgenticPrompt.name == prompt_name,
        )

        if not include_deleted:
            base_query = base_query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))

        db_prompts = base_query.order_by(DatabaseAgenticPrompt.version.desc()).all()

        if not db_prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found for task '{task_id}'")

        prompts = [AgenticPrompt.from_db_model(db_prompt) for db_prompt in db_prompts]
        return AgenticPrompts(prompts=prompts)

    def get_unique_prompt_names(
        self,
        task_id: str,
        include_deleted: bool = False,
    ) -> AgenticPromptNames:
        """Get all unique prompt names for a given task_id."""
        base_query = self.db_session.query(DatabaseAgenticPrompt.name).filter(
            DatabaseAgenticPrompt.task_id == task_id,
        )

        if not include_deleted:
            base_query = base_query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))

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

    def soft_delete_prompt(
        self,
        task_id: str,
        prompt_name: str,
        prompt_version: str,
    ) -> bool:
        """
        Soft delete a prompt by task_id, name and version. This will delete all the data associated with the prompt
        except for task_id, name, created_at, deleted_at and version. If all versions of a prompt are soft-deleted,
        this will permanently delete all versions from the database.

        Parameters:
            task_id: str - the id of the task
            prompt_name: str - the name of the prompt
            prompt_version: str - the version of the prompt

        * Note - Supports:
            - prompt_version='latest' -> marks latest version as deleted
            - prompt_version=<string number> (e.g. '1', '2', etc.) -> marks that version as deleted
            - prompt_version=<datetime> (YYYY-MM-DDTHH:MM:SS, checks to the second) -> marks version created at that time

        Returns:
            - True if all prompt versions for this prompthave been hard-deleted, False if just this one version was soft-deleted
        """
        base_query = self.db_session.query(DatabaseAgenticPrompt).filter(
            DatabaseAgenticPrompt.task_id == task_id,
            DatabaseAgenticPrompt.name == prompt_name,
        )

        if prompt_version == "latest":
            db_prompt = (
                base_query.filter(DatabaseAgenticPrompt.deleted_at.is_(None))
                .order_by(DatabaseAgenticPrompt.version.desc())
                .first()
            )
        elif str(prompt_version).isdigit():
            db_prompt = base_query.filter(
                DatabaseAgenticPrompt.version == int(prompt_version),
            ).first()
        else:
            try:
                target_dt = datetime.fromisoformat(prompt_version)
                db_prompt = (
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

        if not db_prompt:
            raise ValueError(
                f"No matching version of prompt '{prompt_name}' found for task '{task_id}'",
            )

        db_prompt.deleted_at = datetime.now()
        db_prompt.model_name = ""
        db_prompt.model_provider = ""
        db_prompt.messages = []
        db_prompt.tools = None
        db_prompt.config = None

        self.db_session.commit()

        # Check if all versions of this prompt have been soft-deleted
        all_prompts = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt_name,
            )
            .all()
        )

        # deletes all versions of the prompt from the db if all versions have been soft-deleted
        if all_prompts and all(p.deleted_at is not None for p in all_prompts):
            for prompt in all_prompts:
                self.db_session.delete(prompt)
            self.db_session.commit()
            return True

        return False

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
