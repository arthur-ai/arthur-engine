import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from typing import Any, Dict, List, Literal, Optional, Type, Union

from litellm import completion, completion_cost
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import BaseModel
from sqlalchemy.orm import Session


class AgenticPrompt:
    def __init__(
        self,
        name: str,
        messages: List[Dict],
        model_name: str,
        model_provider: str,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, dict]] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stream: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Union[dict, Type[BaseModel]]] = None,
        stop=None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        seed: Optional[int] = None,
        logprobs: Optional[bool] = None,
        top_logprobs: Optional[int] = None,
        logit_bias: Optional[dict] = None,
        stream_options: Optional[dict] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[
            Literal["none", "minimal", "low", "medium", "high", "default"]
        ] = None,
        thinking: Optional[AnthropicThinkingParam] = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.model_name = model_name
        self.messages = messages
        self.tools = tools
        self.model_provider = model_provider
        self.tool_choice = tool_choice
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.stream = stream
        self.max_tokens = max_tokens
        self.response_format = response_format
        self.stop = stop
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.seed = seed
        self.logprobs = logprobs
        self.top_logprobs = top_logprobs
        self.logit_bias = logit_bias
        self.stream_options = stream_options
        self.max_completion_tokens = max_completion_tokens
        self.reasoning_effort = reasoning_effort
        self.thinking = thinking

    def run_chat_completion(self) -> Dict[str, Any]:
        model = self.model_provider + "/" + self.model_name

        response = completion(
            model=model,
            messages=self.messages,
            tools=self.tools,
            tool_choice=self.tool_choice,
            timeout=self.timeout,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            stream=self.stream,
            stop=self.stop,
            presence_penalty=self.presence_penalty,
            frequency_penalty=self.frequency_penalty,
            seed=self.seed,
            logprobs=self.logprobs,
            top_logprobs=self.top_logprobs,
            logit_bias=self.logit_bias,
            max_completion_tokens=self.max_completion_tokens,
            reasoning_effort=self.reasoning_effort,
            thinking=self.thinking,
            stream_options=self.stream_options,
        )

        cost = completion_cost(response)
        msg = response.choices[0].message

        return {
            "content": msg.get("content"),
            "tool_calls": msg.get("tool_calls"),
            "cost": f"{cost:.6f}",
        }


class AgenticPromptRepository:
    def __init__(self, db_session: Session):
        # TODO: actually setup db
        self.db_session = db_session

    def create_prompt(self, **kwargs) -> AgenticPrompt:
        return AgenticPrompt(
            messages=kwargs["messages"],
            name=kwargs["name"],
            model_name=kwargs["model_name"],
            model_provider=kwargs["model_provider"],
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
            temperature=kwargs.get("temperature"),
            top_p=kwargs.get("top_p"),
            max_tokens=kwargs.get("max_tokens"),
            response_format=kwargs.get("response_format"),
            stream=kwargs.get("stream"),
            stop=kwargs.get("stop"),
            presence_penalty=kwargs.get("presence_penalty"),
            frequency_penalty=kwargs.get("frequency_penalty"),
            seed=kwargs.get("seed"),
            logprobs=kwargs.get("logprobs"),
            top_logprobs=kwargs.get("top_logprobs"),
            logit_bias=kwargs.get("logit_bias"),
            stream_options=kwargs.get("stream_options"),
            max_completion_tokens=kwargs.get("max_completion_tokens"),
        )

    def run_prompt(self, prompt: AgenticPrompt) -> str:
        return prompt.run_chat_completion()
