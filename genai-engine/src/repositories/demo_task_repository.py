from datetime import datetime
from typing import List

from arthur_common.models.llm_model_providers import MessageRole, ModelProvider, OpenAIMessage
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from repositories.datasets_repository import DatasetRepository
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.model_provider_repository import ModelProviderRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.internal_schemas import Dataset, NewTraceTransformRequest
from schemas.request_schemas import ContinuousEvalCreateRequest, ContinuousEvalTransformVariableMappingRequest, CreateEvalRequest, CreateAgenticPromptRequest
from schemas.response_schemas import TraceTransformVersionResponse
from services.prompt.chat_completion_service import ChatCompletionService
from services.trace.internal_trace_service import InternalTraceService
from utils.demo_task_resources import (
    DEMO_TASK_DATASET_REQUEST,
    DEMO_TASK_DATASET_ROWS,
    DEMO_TASK_DATASET_VERSION_REQUEST,
    DEMO_TASK_PROMPT_ADHERENCE_EVAL_PROMPT,
    DEMO_TASK_PROMPT_ADHERENCE_EVAL_TRANSFORM,
    DEMO_TASK_SYSTEM_PROMPT,
    DEMO_TASK_CONCISENESS_EVAL_PROMPT,
    DEMO_TASK_CONCISENESS_EVAL_TRANSFORM,
)


class DemoTaskRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.continuous_evals_repo = ContinuousEvalsRepository(db_session)
        self.agentic_prompt_repo = AgenticPromptRepository(db_session)
        self.llm_evals_repo = LLMEvalsRepository(db_session)
        self.trace_transform_repo = TraceTransformRepository(db_session)
        self.dataset_repo = DatasetRepository(db_session)
        self.model_provider_repo = ModelProviderRepository(db_session)
        self.chat_completion_service = ChatCompletionService()
        self.demo_prompt_name = "demo_task_prompt"

    def _get_model_provider_and_name(self) -> tuple[ModelProvider, str]:
        if self.model_provider_repo.get_model_provider_client(ModelProvider.ANTHROPIC) is not None:
            return ModelProvider.ANTHROPIC, "claude-sonnet-4-6"
        if self.model_provider_repo.get_model_provider_client(ModelProvider.OPENAI) is not None:
            return ModelProvider.OPENAI, "gpt-4o"
        else:
            raise ValueError("No model provider found")

    def _create_transform_variable_mapping(self, transform_version: TraceTransformVersionResponse) -> List[ContinuousEvalTransformVariableMappingRequest]:
        return [
            ContinuousEvalTransformVariableMappingRequest(
                transform_variable=transform_version.definition.variables[i].variable_name,
                eval_variable=transform_version.definition.variables[i].variable_name,
            ) for i in range(len(transform_version.definition.variables))
        ]

    def _create_continuous_eval(
        self, 
        task_id: str, 
        eval_name: str,
        eval_instructions: str,
        continuous_eval_name: str,
        continuous_eval_description: str,
        transform_request: NewTraceTransformRequest,
        model_provider: ModelProvider,
        model_name: str,
    ) -> None:
        llm_eval = self.llm_evals_repo.save_llm_item(
            task_id=task_id,
            item_name = eval_name,
            item=CreateEvalRequest(
                model_name=model_name,
                model_provider=model_provider,
                instructions=eval_instructions,
            ),
        )

        transform = self.trace_transform_repo.create_transform(
            task_id=task_id,
            transform=transform_request,
        )

        transform_version = self.trace_transform_repo.list_versions(
            transform_id=transform.id,
        )

        if len(transform_version.versions) == 0:
            raise ValueError("No versions found for prompt adherence transform")

        self.continuous_evals_repo.create_continuous_eval(
            task_id=task_id,
            continuous_eval_request=ContinuousEvalCreateRequest(
                name=continuous_eval_name,
                description=continuous_eval_description,
                llm_eval_name=eval_name,
                llm_eval_version=llm_eval.version,
                transform_id=transform.id,
                transform_version_id=transform_version.versions[0].id,
                transform_variable_mapping=self._create_transform_variable_mapping(transform_version.versions[0]),
            ),
        )

    def _create_demo_prompt(self, task_id: str, model_provider: ModelProvider, model_name: str) -> None:
        """
        Create the demo prompt
        """
        prompt = self.agentic_prompt_repo.save_llm_item(
            task_id=task_id,
            item_name=self.demo_prompt_name,
            item=CreateAgenticPromptRequest(
                model_name=model_name,
                model_provider=model_provider,
                messages=[
                    OpenAIMessage(role=MessageRole.SYSTEM, content=DEMO_TASK_SYSTEM_PROMPT),
                ],
                config=None,
            ),
        )
        self.agentic_prompt_repo.add_tag_to_llm_item_version(
            task_id=task_id,
            item_name=self.demo_prompt_name,
            item_version=str(prompt.version),
            tag="production",
        )

    def _create_demo_dataset(self, task_id: str) -> Dataset:
        dataset = Dataset._from_request_model(task_id, DEMO_TASK_DATASET_REQUEST)
        self.dataset_repo.create_dataset(dataset)
        self.dataset_repo.create_dataset_version(
            dataset_id=dataset.id,
            dataset_version=DEMO_TASK_DATASET_VERSION_REQUEST,
        )
        return dataset

    def _generate_traces(
        self,
        task_id: str,
        model_provider: ModelProvider,
        model_name: str,
        llm_client: LLMClient,
        num_rows: int = 3,
    ) -> None:
        for idx, (query, _) in enumerate(DEMO_TASK_DATASET_ROWS[:num_rows]):
            messages = [OpenAIMessage(role=MessageRole.USER, content=query)]
            prompt = AgenticPrompt(
                name="demo_task_prompt",
                messages=messages,
                model_name=model_name,
                model_provider=model_provider,
                created_at=datetime.now(),
            )

            tracing = InternalTraceService(
                db_session=self.db_session,
                task_id=task_id,
                service_name="demo_task_service",
                enqueue_continuous_evals=True,
            )
            agent_span = tracing.start_agent_span(
                name="demo_task_agent_span",
                agent_name="demo_task_agent",
                session_id=f"demo-session-{idx + 1}",
            )
            tracing.set_input_json(agent_span, {"text": query})

            llm_span = tracing.start_llm_span(agent_span, model_name, model_provider)
            tracing.set_llm_input_messages(llm_span, messages)

            response = self.chat_completion_service.run_chat_completion(prompt, llm_client)
            response_content = response.content or ""

            tracing.set_llm_response(
                llm_span,
                content=response_content,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
            )
            tracing.end_span(llm_span)

            tracing.set_output_json(agent_span, {"text": response_content})
            tracing.end_span(agent_span)
            tracing.flush()

    def create_demo_items_for_task(self, task_id: str) -> None:
        model_provider, model_name = self._get_model_provider_and_name()
        llm_client = self.model_provider_repo.get_model_provider_client(model_provider)

        # Create demo prompt
        self._create_demo_prompt(task_id=task_id, model_provider=model_provider, model_name=model_name)

        # Create demo continuous evals
        self._create_continuous_eval(
            task_id=task_id,
            eval_name="Prompt Adherence Eval",
            eval_instructions=DEMO_TASK_PROMPT_ADHERENCE_EVAL_PROMPT,
            continuous_eval_name="Prompt Adherence Continuous Eval",
            continuous_eval_description="Evaluates if the assistant's final response adheres to the prompt.",
            transform_request=DEMO_TASK_PROMPT_ADHERENCE_EVAL_TRANSFORM,
            model_provider=model_provider,
            model_name=model_name,
        )

        self._create_continuous_eval(
            task_id=task_id,
            eval_name="Conciseness Eval",
            eval_instructions=DEMO_TASK_CONCISENESS_EVAL_PROMPT,
            continuous_eval_name="Conciseness Continuous Eval",
            continuous_eval_description="Evaluates if the response is concise.",
            transform_request=DEMO_TASK_CONCISENESS_EVAL_TRANSFORM,
            model_provider=model_provider,
            model_name=model_name,
        )

        # Create demo dataset
        self._create_demo_dataset(task_id=task_id)

        # Generate traces
        self._generate_traces(task_id=task_id, model_provider=model_provider, model_name=model_name, llm_client=llm_client)