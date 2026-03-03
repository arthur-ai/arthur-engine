import importlib
import json
import logging
import os
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes

from arthur_observability_sdk._client import ArthurAPIClient
from arthur_observability_sdk.telemetry import setup_telemetry

logger = logging.getLogger(__name__)


class Arthur:
    """
    Main entrypoint for the Arthur Observability SDK.

    Handles:
    - OTel telemetry setup (TracerProvider, OTLP export)
    - Prompt management (``get_prompt``)
    - Framework instrumentation (``instrument_langchain``, etc.)

    At least one of ``task_id``, ``task_name``, or ``service_name`` must be
    provided — otherwise a ``ValueError`` is raised at construction time.

    Args:
        api_key: Arthur API key. Falls back to ``ARTHUR_API_KEY`` env var.
        base_url: Base URL of the Arthur GenAI Engine.  Falls back to
            ``ARTHUR_BASE_URL`` env var, then ``http://localhost:3030``.
        service_name: OTel ``service.name`` resource attribute.
        resource_attributes: Additional OTel resource attributes.
        task_id: Arthur task UUID used for prompt fetching.
        task_name: Arthur task name — resolved lazily to a UUID via the API.
        enable_telemetry: When False, no TracerProvider is created.
        otlp_endpoint: OTLP HTTP traces endpoint.  Defaults to
            ``{base_url}/v1/traces``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:3030",
        service_name: Optional[str] = None,
        resource_attributes: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        task_name: Optional[str] = None,
        enable_telemetry: bool = True,
        otlp_endpoint: Optional[str] = None,
    ) -> None:
        self._api_key: Optional[str] = api_key or os.environ.get("ARTHUR_API_KEY")
        self._base_url: str = os.environ.get("ARTHUR_BASE_URL", base_url).rstrip("/")
        self._service_name: Optional[str] = service_name
        self._resource_attributes: Dict[str, Any] = resource_attributes or {}
        self._task_id: Optional[str] = task_id
        self._task_name: Optional[str] = task_name
        self._enable_telemetry: bool = enable_telemetry
        self._otlp_endpoint: str = otlp_endpoint or f"{self._base_url}/api/v1/traces"

        if task_id is None and task_name is None and service_name is None:
            raise ValueError(
                "Arthur requires at least one of: task_id, task_name, or service_name. "
                "Provide a task context for prompt fetching or a service_name for telemetry."
            )

        self._tracer_provider: Optional[TracerProvider] = None
        if enable_telemetry:
            effective_service_name = service_name or task_name or task_id or "arthur-app"
            self._tracer_provider = setup_telemetry(
                service_name=effective_service_name,
                otlp_endpoint=self._otlp_endpoint,
                api_key=self._api_key,
                resource_attributes=self._resource_attributes,
            )

        self._api_client: ArthurAPIClient = ArthurAPIClient(
            base_url=self._base_url,
            api_key=self._api_key,
        )

        self._resolved_task_id: Optional[str] = task_id

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def task_id(self) -> Optional[str]:
        """The resolved task UUID, or None if not yet resolved."""
        return self._resolved_task_id

    @property
    def task_name(self) -> Optional[str]:
        """The task name provided at construction time."""
        return self._task_name

    @property
    def telemetry_active(self) -> bool:
        """True when a TracerProvider has been configured."""
        return self._tracer_provider is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_task_id(self, override: Optional[str] = None) -> str:
        if override:
            return override
        if self._resolved_task_id:
            return self._resolved_task_id
        if self._task_name:
            logger.debug("Resolving task_id for task_name='%s'", self._task_name)
            self._resolved_task_id = self._api_client.resolve_task_id(self._task_name)
            return self._resolved_task_id
        raise ValueError(
            "No task_id available. Provide task_id or task_name when initialising Arthur."
        )

    def _instrument(self, package: str, extra_name: str, module_path: str, class_name: str) -> Any:
        try:
            mod = importlib.import_module(module_path)
        except ImportError:
            raise ImportError(
                f"Missing optional dependency '{package}'. "
                f"Install it with: pip install arthur-observability-sdk[{extra_name}]"
            )
        instrumentor_cls = getattr(mod, class_name)
        instrumentor = instrumentor_cls()
        kwargs: Dict[str, Any] = {}
        if self._tracer_provider is not None:
            kwargs["tracer_provider"] = self._tracer_provider
        instrumentor.instrument(**kwargs)
        return instrumentor

    # ------------------------------------------------------------------
    # Prompt management
    # ------------------------------------------------------------------

    def get_prompt(
        self,
        name: str,
        version: str = "latest",
        tag: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetches a prompt from the Arthur GenAI Engine and emits an OTel PROMPT span.

        Args:
            name: Prompt name.
            version: Version string (e.g. ``'latest'``, ``'1'``, ``'2'``).
                Ignored when ``tag`` is provided.
            tag: Tag name — when set, uses the by-tag endpoint.
            task_id: Overrides the instance-level ``task_id`` for this call.

        Returns:
            The raw prompt dict from the API (matches ``AgenticPrompt`` schema).
        """
        resolved_task_id = self._get_task_id(task_id)
        tracer_provider = self._tracer_provider or trace.get_tracer_provider()
        tracer = tracer_provider.get_tracer("openinference.instrumentation.arthur")

        with tracer.start_as_current_span("get_prompt") as span:
            span.set_attribute(
                SpanAttributes.OPENINFERENCE_SPAN_KIND,
                OpenInferenceSpanKindValues.PROMPT.value,
            )
            span.set_attribute("arthur.prompt.name", name)
            span.set_attribute("arthur.task.id", resolved_task_id)

            resolved_version = tag if tag else version
            span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE_VERSION, resolved_version)

            try:
                if tag:
                    prompt_data = self._api_client.get_prompt_by_tag(
                        task_id=resolved_task_id, name=name, tag=tag
                    )
                else:
                    prompt_data = self._api_client.get_prompt_by_version(
                        task_id=resolved_task_id, name=name, version=version
                    )
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise

            messages = prompt_data.get("messages", [])
            template_str = json.dumps(messages)
            variables = prompt_data.get("variables", [])

            span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE, template_str)
            span.set_attribute(
                SpanAttributes.LLM_PROMPT_TEMPLATE_VARIABLES, json.dumps(variables)
            )
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(prompt_data))
            span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

        return prompt_data

    def render_prompt(
        self,
        name: str,
        variables: Dict[str, str],
        version: str = "latest",
        tag: Optional[str] = None,
        strict: bool = False,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Renders a saved prompt by substituting ``variables`` into its template
        and returns the result with ``{{variable}}`` placeholders replaced.

        Calls ``POST /api/v1/tasks/{task_id}/prompts/{name}/versions/{version}/renders``.
        When ``tag`` is provided it is passed as the version path segment — the
        engine accepts tag names (e.g. ``"latest"``) in that position.

        Args:
            name: Prompt name.
            variables: Mapping of variable name → value to substitute.
            version: Version string (``'latest'``, ``'1'``, ``'2'``, …).
                Ignored when ``tag`` is provided.
            tag: Tag name — when set, used as the version path segment so
                the engine resolves the tagged version and renders it.
            strict: When True the engine raises if any template variable is
                missing from ``variables``.
            task_id: Overrides the instance-level ``task_id`` for this call.

        Returns:
            The rendered ``AgenticPrompt`` dict with substituted messages.
        """
        resolved_task_id = self._get_task_id(task_id)
        effective_version = tag if tag else version

        tracer_provider = self._tracer_provider or trace.get_tracer_provider()
        tracer = tracer_provider.get_tracer("openinference.instrumentation.arthur")

        with tracer.start_as_current_span("render_prompt") as span:
            span.set_attribute(
                SpanAttributes.OPENINFERENCE_SPAN_KIND,
                OpenInferenceSpanKindValues.PROMPT.value,
            )
            span.set_attribute("arthur.prompt.name", name)
            span.set_attribute("arthur.task.id", resolved_task_id)
            span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE_VERSION, effective_version)

            try:
                # Fetch the original template (with {{ variable }} markers) so
                # the span INPUT shows the unrendered prompt + variable values,
                # not the already-substituted result.
                if tag:
                    template_data = self._api_client.get_prompt_by_tag(
                        task_id=resolved_task_id, name=name, tag=tag
                    )
                else:
                    template_data = self._api_client.get_prompt_by_version(
                        task_id=resolved_task_id, name=name, version=version
                    )

                prompt_data = self._api_client.render_prompt(
                    task_id=resolved_task_id,
                    name=name,
                    version=effective_version,
                    variables=variables,
                    strict=strict,
                )
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise

            # INPUT: original template messages (with markers) + variable values
            template_messages = template_data.get("messages", [])
            span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE, json.dumps(template_messages))
            span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE_VARIABLES, json.dumps(variables))
            span.set_attribute(
                SpanAttributes.INPUT_VALUE,
                json.dumps({"messages": template_messages, "variables": variables}),
            )
            span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")

            # OUTPUT: rendered result (variables substituted)
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(prompt_data))
            span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

        return prompt_data

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        if self._tracer_provider is not None:
            self._tracer_provider.shutdown()
        self._api_client.close()

    # ------------------------------------------------------------------
    # Named instrumentation methods (32 frameworks)
    # ------------------------------------------------------------------

    def instrument_agent_framework(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-agent-framework",
            "agent-framework",
            "openinference.instrumentation.agent_framework",
            "AgentFrameworkInstrumentor",
        )

    def instrument_agentspec(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-agentspec",
            "agentspec",
            "openinference.instrumentation.agentspec",
            "AgentSpecInstrumentor",
        )

    def instrument_agno(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-agno",
            "agno",
            "openinference.instrumentation.agno",
            "AgnoInstrumentor",
        )

    def instrument_anthropic(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-anthropic",
            "anthropic",
            "openinference.instrumentation.anthropic",
            "AnthropicInstrumentor",
        )

    def instrument_autogen(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-autogen",
            "autogen",
            "openinference.instrumentation.autogen",
            "AutogenInstrumentor",
        )

    def instrument_autogen_agentchat(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-autogen-agentchat",
            "autogen-agentchat",
            "openinference.instrumentation.autogen_agentchat",
            "AutogenAgentChatInstrumentor",
        )

    def instrument_bedrock(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-bedrock",
            "bedrock",
            "openinference.instrumentation.bedrock",
            "BedrockInstrumentor",
        )

    def instrument_beeai(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-beeai",
            "beeai",
            "openinference.instrumentation.beeai",
            "BeeAIInstrumentor",
        )

    def instrument_crewai(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-crewai",
            "crewai",
            "openinference.instrumentation.crewai",
            "CrewAIInstrumentor",
        )

    def instrument_dspy(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-dspy",
            "dspy",
            "openinference.instrumentation.dspy",
            "DSPyInstrumentor",
        )

    def instrument_google_adk(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-google-adk",
            "google-adk",
            "openinference.instrumentation.google_adk",
            "GoogleADKInstrumentor",
        )

    def instrument_google_genai(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-google-genai",
            "google-genai",
            "openinference.instrumentation.google_genai",
            "GoogleGenAIInstrumentor",
        )

    def instrument_groq(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-groq",
            "groq",
            "openinference.instrumentation.groq",
            "GroqInstrumentor",
        )

    def instrument_guardrails(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-guardrails",
            "guardrails",
            "openinference.instrumentation.guardrails",
            "GuardrailsInstrumentor",
        )

    def instrument_haystack(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-haystack",
            "haystack",
            "openinference.instrumentation.haystack",
            "HaystackInstrumentor",
        )

    def instrument_instructor(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-instructor",
            "instructor",
            "openinference.instrumentation.instructor",
            "InstructorInstrumentor",
        )

    def instrument_langchain(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-langchain",
            "langchain",
            "openinference.instrumentation.langchain",
            "LangChainInstrumentor",
        )

    def instrument_litellm(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-litellm",
            "litellm",
            "openinference.instrumentation.litellm",
            "LiteLLMInstrumentor",
        )

    def instrument_llama_index(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-llama-index",
            "llama-index",
            "openinference.instrumentation.llama_index",
            "LlamaIndexInstrumentor",
        )

    def instrument_mcp(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-mcp",
            "mcp",
            "openinference.instrumentation.mcp",
            "MCPInstrumentor",
        )

    def instrument_mistralai(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-mistralai",
            "mistralai",
            "openinference.instrumentation.mistralai",
            "MistralAIInstrumentor",
        )

    def instrument_openai(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-openai",
            "openai",
            "openinference.instrumentation.openai",
            "OpenAIInstrumentor",
        )

    def instrument_openai_agents(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-openai-agents",
            "openai-agents",
            "openinference.instrumentation.openai_agents",
            "OpenAIAgentsInstrumentor",
        )

    def instrument_openlit(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-openlit",
            "openlit",
            "openinference.instrumentation.openlit",
            "OpenLITInstrumentor",
        )

    def instrument_openllmetry(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-openllmetry",
            "openllmetry",
            "openinference.instrumentation.openllmetry",
            "OpenLLMetryInstrumentor",
        )

    def instrument_pipecat(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-pipecat",
            "pipecat",
            "openinference.instrumentation.pipecat",
            "PipecatInstrumentor",
        )

    def instrument_portkey(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-portkey",
            "portkey",
            "openinference.instrumentation.portkey",
            "PortkeyInstrumentor",
        )

    def instrument_pydantic_ai(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-pydantic-ai",
            "pydantic-ai",
            "openinference.instrumentation.pydantic_ai",
            "PydanticAIInstrumentor",
        )

    def instrument_smolagents(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-smolagents",
            "smolagents",
            "openinference.instrumentation.smolagents",
            "SmolAgentsInstrumentor",
        )

    def instrument_strands_agents(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-strands-agents",
            "strands-agents",
            "openinference.instrumentation.strands_agents",
            "StrandsAgentsInstrumentor",
        )

    def instrument_vertexai(self) -> Any:
        return self._instrument(
            "openinference-instrumentation-vertexai",
            "vertexai",
            "openinference.instrumentation.vertexai",
            "VertexAIInstrumentor",
        )
