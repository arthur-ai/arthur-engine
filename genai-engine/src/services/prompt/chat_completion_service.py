from typing import Any, AsyncGenerator, Dict, List, Set, Tuple, Union

from fastapi.responses import StreamingResponse
from jinja2 import meta
from jinja2.sandbox import SandboxedEnvironment
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

    def __init__(self):
        # autoescape=False because Jinja automatically HTML-escapes items by default. Ex:
        #   if text = "{{ name }}" and variables = {"name": "<Bob>"}
        #   autoescape=False "{{ name }}" -> "<Bob>"
        #   autoescape=True "{{ name }}" -> "&lt;Bob&gt;"
        self._jinja_env = SandboxedEnvironment(autoescape=False)

    # ============================================================================
    # Variable Validation and Replacement
    # ============================================================================

    def find_undeclared_variables_in_text(
        self,
        text: str,
    ) -> Set[str]:
        template_ast = self._jinja_env.parse(text)
        return meta.find_undeclared_variables(template_ast)

    def _find_missing_variables_in_variable_map(
        self,
        variable_map: Dict[str, str],
        text: str,
    ) -> List[str]:
        undeclared_vars = self.find_undeclared_variables_in_text(text)
        return [v for v in undeclared_vars if v not in variable_map]

    def find_missing_variables_in_messages(
        self,
        variable_map: Dict[str, str],
        messages: List[OpenAIMessage],
    ) -> Set[str]:
        missing_vars = set()
        for message in messages:
            if message.content is None:
                continue

            if isinstance(message.content, str):
                missing_vars.update(
                    self._find_missing_variables_in_variable_map(
                        variable_map,
                        message.content,
                    ),
                )
            elif isinstance(message.content, list):
                for item in message.content:
                    if item.type == OpenAIMessageType.TEXT.value and item.text:
                        missing_vars.update(
                            self._find_missing_variables_in_variable_map(
                                variable_map,
                                item.text,
                            ),
                        )

        return missing_vars

    def _replace_variables_in_text(
        self,
        variable_map: Dict[str, str],
        text: str,
    ) -> str:
        template = self._jinja_env.from_string(text)
        return template.render(**variable_map)

    def replace_variables(
        self,
        variable_map: Dict[str, str],
        messages: List[OpenAIMessage],
    ) -> list[dict]:
        for message in messages:
            if message.content is None:
                continue

            if isinstance(message.content, str):
                message.content = self._replace_variables_in_text(
                    variable_map,
                    message.content,
                )
            elif isinstance(message.content, list):
                for item in message.content:
                    if item.type == OpenAIMessageType.TEXT.value and item.text:
                        item.text = self._replace_variables_in_text(
                            variable_map,
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

        completion_params = {
            "messages": [
                message.model_dump(exclude_none=True) for message in prompt.messages
            ],
        }

        if prompt.tools:
            completion_params["tools"] = [
                tool.model_dump(exclude_none=True) for tool in prompt.tools
            ]

        # flatten config params to pass into litellm properly
        if prompt.config:
            if prompt.config.timeout:
                completion_params["timeout"] = prompt.config.timeout
            if prompt.config.temperature:
                completion_params["temperature"] = prompt.config.temperature
            if prompt.config.top_p:
                completion_params["top_p"] = prompt.config.top_p
            if prompt.config.max_tokens:
                completion_params["max_tokens"] = prompt.config.max_tokens
            if prompt.config.stop:
                completion_params["stop"] = prompt.config.stop
            if prompt.config.presence_penalty:
                completion_params["presence_penalty"] = prompt.config.presence_penalty
            if prompt.config.frequency_penalty:
                completion_params["frequency_penalty"] = prompt.config.frequency_penalty
            if prompt.config.seed:
                completion_params["seed"] = prompt.config.seed
            if prompt.config.logprobs:
                completion_params["logprobs"] = prompt.config.logprobs
            if prompt.config.top_logprobs:
                completion_params["top_logprobs"] = prompt.config.top_logprobs
            if prompt.config.logit_bias:
                completion_params["logit_bias"] = prompt.config.logit_bias.model_dump(
                    exclude_none=True,
                )
            if prompt.config.max_completion_tokens:
                completion_params["max_completion_tokens"] = (
                    prompt.config.max_completion_tokens
                )
            if prompt.config.reasoning_effort:
                completion_params["reasoning_effort"] = (
                    prompt.config.reasoning_effort.value
                )
            if prompt.config.thinking:
                completion_params["thinking"] = dict(prompt.config.thinking)
            if prompt.config.tool_choice:
                if isinstance(prompt.config.tool_choice, ToolChoiceEnum):
                    completion_params["tool_choice"] = prompt.config.tool_choice.value
                else:
                    completion_params["tool_choice"] = (
                        prompt.config.tool_choice.model_dump(exclude_none=True)
                    )
            if prompt.config.response_format:
                # either get the json_object/schema response format or pass in the pydantic model
                response_format = prompt.config.response_format
                if isinstance(response_format, LLMResponseFormat):
                    completion_params["response_format"] = response_format.model_dump(
                        exclude_none=True,
                    )
                else:
                    completion_params["response_format"] = response_format
            if prompt.config.stream_options:
                completion_params["stream_options"] = (
                    prompt.config.stream_options.model_dump(exclude_none=True)
                )

        # validate all variables are passed in to the prompt if strict mode is enabled
        if completion_request.strict == True:
            missing_vars = self.find_missing_variables_in_messages(
                completion_request._variable_map,
                prompt.messages,
            )
            if missing_vars:
                raise ValueError(
                    f"Missing values for the following variables: {', '.join(sorted(missing_vars))}",
                )

        # replace variables in messages
        completion_messages = prompt.messages
        if completion_request.variables:
            completion_messages = self.replace_variables(
                completion_request._variable_map,
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
