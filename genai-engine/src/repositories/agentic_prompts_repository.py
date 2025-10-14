from typing import Any, Dict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from schemas.agentic_prompt_schemas import (
    AgenticPrompt,
    AgenticPromptRunConfig,
    AgenticPrompts,
    AgenticPromptUnsavedRunConfig,
)
from schemas.response_schemas import AgenticPromptRunResponse


class AgenticPromptRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_prompt(self, **kwargs) -> AgenticPrompt:
        return AgenticPrompt(**kwargs)

    def run_unsaved_prompt(
        self,
        run_config: AgenticPromptUnsavedRunConfig,
    ) -> AgenticPromptRunResponse:
        return run_config.run_unsaved_prompt()

    def run_saved_prompt(
        self,
        task_id: str,
        prompt_name: str,
        run_config: AgenticPromptRunConfig = AgenticPromptRunConfig(),
    ) -> AgenticPromptRunResponse:
        prompt = self.get_prompt(task_id, prompt_name)
        return prompt.run_chat_completion(run_config)

    def get_prompt(self, task_id: str, prompt_name: str) -> AgenticPrompt:
        """Get a prompt by task_id and name, return as AgenticPrompt object"""
        db_prompt = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt_name,
            )
            .first()
        )

        if not db_prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found for task '{task_id}'")

        # Convert database model back to AgenticPrompt object
        return AgenticPrompt.from_db_model(db_prompt)

    def get_all_prompts(self, task_id: str) -> AgenticPrompts:
        """Get all prompts by task_id, return as list of AgenticPrompt objects"""
        db_prompts = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(DatabaseAgenticPrompt.task_id == task_id)
            .all()
        )

        prompts = [AgenticPrompt.from_db_model(db_prompt) for db_prompt in db_prompts]
        return AgenticPrompts(prompts=prompts)

    def save_prompt(self, task_id: str, prompt: AgenticPrompt | Dict[str, Any]) -> None:
        """Save an AgenticPrompt to the database"""
        if isinstance(prompt, dict):
            prompt = self.create_prompt(**prompt)

        db_prompt = prompt.to_db_model(task_id)

        try:
            self.db_session.add(db_prompt)
            self.db_session.commit()
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Prompt '{prompt.name}' already exists for task '{task_id}'",
            )

    def delete_prompt(self, task_id: str, prompt_name: str) -> None:
        """Delete an agentic prompt from the database"""
        db_prompt = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt_name,
            )
            .first()
        )

        if not db_prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found for task '{task_id}'")

        self.db_session.delete(db_prompt)
        self.db_session.commit()
