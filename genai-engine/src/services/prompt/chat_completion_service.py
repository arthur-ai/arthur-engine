from typing import Any, AsyncGenerator, Dict, List, Set, Tuple, Union

from fastapi.responses import StreamingResponse
from jinja2 import meta
from litellm import (
    completion_cost,
    stream_chunk_builder,
)

from clients.llm.llm_client import LLMClient, LLMModelResponse
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.enums import OpenAIMessageType
from schemas.llm_schemas import LLMResponseFormat, OpenAIMessage
from schemas.request_schemas import CompletionRequest, PromptCompletionRequest
from schemas.response_schemas import AgenticPromptRunResponse


class ChatCompletionService:
    """Service for running a chat completion"""

    # ============================================================================
    # Variable Validation and Replacement
    # ============================================================================

    def _find_missing_variables_in_text(
        self,
        completion_request: PromptCompletionRequest,
        text: str,
    ) -> List[str]:
        template_ast = completion_request._jinja_env.parse(text)
        undeclared_vars = meta.find_undeclared_variables(template_ast)
        return [v for v in undeclared_vars if v not in completion_request._variable_map]

    def _find_missing_variables(
        self,
        completion_request: PromptCompletionRequest,
        messages: List[OpenAIMessage],
    ) -> Set[str]:
        missing_vars = set()
        for message in messages:
            if message.content is None:
                continue

            if isinstance(message.content, str):
                missing_vars.update(
                    self._find_missing_variables_in_text(
                        completion_request,
                        message.content,
                    ),
                )
            elif isinstance(message.content, list):
                for item in message.content:
                    if item.type == OpenAIMessageType.TEXT.value and item.text:
                        missing_vars.update(
                            self._find_missing_variables_in_text(
                                completion_request,
                                item.text,
                            ),
                        )

        return missing_vars

    def _replace_variables_in_text(
        self,
        completion_request: PromptCompletionRequest,
        text: str,
    ) -> str:
        template = completion_request._jinja_env.from_string(text)
        return template.render(**completion_request._variable_map)

    def _replace_variables(
        self,
        completion_request: PromptCompletionRequest,
        messages: List[OpenAIMessage],
    ) -> list[dict]:
        for message in messages:
            if message.content is None:
                continue

            if isinstance(message.content, str):
                message.content = self._replace_variables_in_text(
                    completion_request,
                    message.content,
                )
            elif isinstance(message.content, list):
                for item in message.content:
                    if item.type == OpenAIMessageType.TEXT.value and item.text:
                        item.text = self._replace_variables_in_text(
                            completion_request,
                            item.text,
                        )

        return messages

    @staticmethod
    def to_prompt_and_request(
        unsaved_prompt: CompletionRequest,
    ) -> Tuple[AgenticPrompt, PromptCompletionRequest]:
        """
        Convert an unsaved run request into its corresponding AgenticPrompt and PromptCompletionRequest
        """
        prompt = AgenticPrompt(
            name="test_unsaved_prompt",
            **unsaved_prompt.model_dump(exclude={"completion_request"}),
        )
        return prompt, unsaved_prompt.completion_request

    # ============================================================================
    # Completion Helpers and Methods
    # ============================================================================

    def _get_completion_params(
        self,
        prompt: AgenticPrompt,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> Tuple[str, Dict[str, Any]]:
        model = prompt.model_provider + "/" + prompt.model_name

        completion_params = prompt.model_dump(
            exclude={
                "name",
                "model_name",
                "model_provider",
                "created_at",
                "version",
                "deleted_at",
                "messages",
                "config",
            },
            exclude_none=True,
        )

        if prompt.config:
            # flatten config params to pass into litellm properly
            config_dict = prompt.config.model_dump(
                exclude={"response_format"},
                exclude_none=True,
            )
            completion_params.update(config_dict)

            # either get the json_object/schema response format or pass in the pydantic model
            if prompt.config.response_format:
                response_format = prompt.config.response_format
                if isinstance(response_format, LLMResponseFormat):
                    completion_params["response_format"] = response_format.model_dump(
                        exclude_none=True,
                    )
                else:
                    completion_params["response_format"] = response_format

        # validate all variables are passed in to the prompt if strict mode is enabled
        if completion_request.strict == True:
            missing_vars = self._find_missing_variables(
                completion_request,
                prompt.messages,
            )
            if missing_vars:
                raise ValueError(
                    f"Missing values for the following variables: {', '.join(sorted(missing_vars))}",
                )

        # replace variables in messages
        completion_messages = prompt.messages
        if completion_request.variables:
            completion_messages = self._replace_variables(
                completion_request,
                completion_messages,
            )

        completion_params["messages"] = [
            message.model_dump(exclude_none=True) for message in completion_messages
        ]

        if completion_request.stream is not None:
            completion_params["stream"] = completion_request.stream

        # not allowed to have tool_choice if no tools are provided
        if prompt.tools is None:
            completion_params.pop("tool_choice", None)

        return model, completion_params

    def run_chat_completion_raw_response(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> LLMModelResponse:
        model, completion_params = self._get_completion_params(
            prompt,
            completion_request,
        )
        return llm_client.completion(model=model, **completion_params)

    def run_chat_completion(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> AgenticPromptRunResponse:
        if prompt.has_been_deleted():
            raise ValueError(
                f"Cannot run chat completion for this prompt because it was deleted on: {prompt.deleted_at}",
            )

        llm_model_response = self.run_chat_completion_raw_response(
            prompt,
            llm_client,
            completion_request,
        )
        msg = llm_model_response.response.choices[0].message

        return AgenticPromptRunResponse(
            content=msg.get("content"),
            tool_calls=msg.get("tool_calls"),
            cost=f"{llm_model_response.cost:.6f}",
        )

    async def stream_chat_completion(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> AsyncGenerator[str, None]:
        try:
            if prompt.has_been_deleted():
                raise ValueError(
                    f"Cannot stream chat completion for this prompt because it was deleted on: {prompt.deleted_at}",
                )

            model, completion_params = self._get_completion_params(
                prompt,
                completion_request,
            )
            response = await llm_client.acompletion(model=model, **completion_params)

            collected_chunks = []
            async for chunk in response:
                collected_chunks.append(chunk)
                yield f"event: chunk\ndata: {chunk.model_dump_json()}\n\n"

            complete_response = stream_chunk_builder(
                collected_chunks,
                messages=completion_params.get("messages", []),
            )

            cost = completion_cost(complete_response)
            msg = complete_response.choices[0].message

            yield f"event: final_response\ndata: {
                AgenticPromptRunResponse(
                    content=msg.get("content"),
                    tool_calls=msg.get("tool_calls"),
                    cost=f"{cost:.6f}",
                ).model_dump_json()
            }\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    async def execute_prompt_completion(
        self,
        llm_client: LLMClient,
        prompt: AgenticPrompt,
        completion_request: PromptCompletionRequest,
    ) -> Union[AgenticPromptRunResponse, StreamingResponse]:
        """Helper to execute prompt completion with or without streaming"""
        if completion_request.stream is None or completion_request.stream == False:
            return self.run_chat_completion(prompt, llm_client, completion_request)

        return StreamingResponse(
            self.stream_chat_completion(prompt, llm_client, completion_request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
