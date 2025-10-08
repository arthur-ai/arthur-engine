from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Type, Union

from litellm import completion, completion_cost
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models.agentic_prompt_models import DatabaseAgenticPrompt


class AgenticPromptRunResponse(BaseModel):
    content: str
    tool_calls: Optional[List[Dict]] = None
    cost: str


class AgenticPrompt(BaseModel):
    name: str
    messages: List[Dict]
    model_name: str
    model_provider: str
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[Union[str, dict]] = None
    timeout: Optional[float] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stream: Optional[bool] = None
    max_tokens: Optional[int] = None
    response_format: Optional[Union[dict, Type[BaseModel]]] = None
    stop: Optional[str] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    seed: Optional[int] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    logit_bias: Optional[dict] = None
    max_completion_tokens: Optional[int] = None
    reasoning_effort: Optional[
        Literal["none", "minimal", "low", "medium", "high", "default"]
    ] = None
    thinking: Optional[AnthropicThinkingParam] = None
    stream_options: Optional[dict] = None

    def run_chat_completion(self) -> Dict[str, Any]:
        model = self.model_provider + "/" + self.model_name

        completion_params = self.model_dump(
            exclude={"name", "model_name", "model_provider"},
        )

        response = completion(model=model, **completion_params)

        cost = completion_cost(response)
        msg = response.choices[0].message

        return AgenticPromptRunResponse(
            content=msg.get("content"),
            tool_calls=msg.get("tool_calls"),
            cost=f"{cost:.6f}",
        )

    @classmethod
    def from_db_model(cls, db_prompt: DatabaseAgenticPrompt) -> "AgenticPrompt":
        return cls(**db_prompt.__dict__)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AgenticPrompts(BaseModel):
    prompts: List[AgenticPrompt]


class AgenticPromptRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_prompt(self, **kwargs) -> AgenticPrompt:
        return AgenticPrompt(**kwargs)

    def run_prompt(self, prompt: AgenticPrompt) -> AgenticPromptRunResponse:
        return prompt.run_chat_completion()

    def run_saved_prompt(
        self,
        task_id: str,
        prompt_name: str,
    ) -> AgenticPromptRunResponse:
        prompt = self.get_prompt(task_id, prompt_name)
        return prompt.run_chat_completion()

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

        db_prompt = DatabaseAgenticPrompt(
            task_id=task_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            **prompt.model_dump(),
        )

        try:
            self.db_session.add(db_prompt)
            self.db_session.commit()
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Prompt '{prompt.name}' already exists for task '{task_id}'",
            )

    def update_prompt(
        self,
        task_id: str,
        prompt: AgenticPrompt | Dict[str, Any],
    ) -> None:
        """Update an existing agentic prompt in the database"""
        if isinstance(prompt, AgenticPrompt):
            prompt = prompt.to_dict()

        # Get the existing prompt
        db_prompt = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt["name"],
            )
            .first()
        )

        if not db_prompt:
            raise ValueError(
                f"Prompt '{prompt["name"]}' not found for task '{task_id}'",
            )

        # Update the fields
        updated_field = False
        for field, value in prompt.items():
            if hasattr(db_prompt, field) and value != getattr(db_prompt, field):
                setattr(db_prompt, field, value)
                updated_field = True

        if not updated_field:
            raise ValueError(f"No fields to update for prompt '{prompt['name']}'")

        db_prompt.updated_at = datetime.now()

        try:
            self.db_session.commit()
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Error updating prompt '{prompt['name']}' for task '{task_id}'",
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
