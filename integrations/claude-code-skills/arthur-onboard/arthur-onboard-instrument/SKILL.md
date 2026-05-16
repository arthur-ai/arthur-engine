---
name: arthur-onboard-instrument
description: Arthur onboarding sub-skill — Step 5: Instrument the target repository with Arthur tracing (Python SDK, Mastra TS, or OpenInference). Reads detection results from .arthur-engine.env.
allowed-tools: Bash, Read, Write, Edit, Task
---

# Arthur Onboard — Step 5: Instrument Code

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`, `ARTHUR_DETECTED_LANGUAGE`, `ARTHUR_DETECTED_FRAMEWORK`, `ARTHUR_IS_INSTRUMENTED`.

---

## If Already Instrumented

If `ARTHUR_IS_INSTRUMENTED=true`: tell the user, exit this skill.

---

## Choose Instrumentation Approach

Based on detection results:
- Python app → `arthur-sdk` (preferred)
- Mastra TypeScript → `mastra-arthur`
- Other TypeScript/JavaScript or Python without arthur-sdk → `openinference`

Show the planned changes and ask user to confirm before proceeding.

**Delegate to a Task sub-agent.** Replace `<PLACEHOLDERS>` with actual values from state.

---

## Python — arthur-sdk Instrumentation Task Prompt

```
You are an expert Python developer. Instrument the agentic application at: <REPO_PATH>

Arthur Engine URL: <ARTHUR_ENGINE_URL>
Arthur Task ID: <ARTHUR_TASK_ID>

RULES:
- Never hardcode API keys. Always read from env vars.
- Add to .env (create if missing; ensure .env is gitignored):
    ARTHUR_API_KEY=$ARTHUR_API_KEY
    ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
    ARTHUR_TASK_ID=<ARTHUR_TASK_ID>
- Add placeholders to .env.example.
- Smallest possible changes — instrument, don't refactor.
- Print final JSON on the last line: {"success":true,"testsPassed":true,"summary":"<one sentence>"}

STEP 1 — ANALYSIS:
- Read requirements.txt / pyproject.toml (note package manager: pip/uv/poetry)
- Find the entry point (main.py, app.py, __main__.py, or similar)
- Identify the LLM framework in use. Match it to one of the supported SDK extras below.
- Check if arthur_observability_sdk already installed (skip STEP 2 if yes)

STEP 2 — IMPLEMENTATION:

PART A — SDK SETUP:

  Supported framework extras and their instrument methods — pick the one that matches:
    openai              → instrument_openai()
    langchain           → instrument_langchain()
    anthropic           → instrument_anthropic()
    crewai              → instrument_crewai()
    autogen             → instrument_autogen()
    autogen-agentchat   → instrument_autogen_agentchat()
    llama-index         → instrument_llama_index()
    bedrock             → instrument_bedrock()
    vertexai            → instrument_vertexai()
    google-genai        → instrument_google_genai()
    google-adk          → instrument_google_adk()
    mistralai           → instrument_mistralai()
    groq                → instrument_groq()
    litellm             → instrument_litellm()
    pydantic-ai         → instrument_pydantic_ai()
    openai-agents       → instrument_openai_agents()
    claude-agent-sdk    → instrument_claude_agent_sdk()
    haystack            → instrument_haystack()
    dspy                → instrument_dspy()
    smolagents          → instrument_smolagents()
    strands-agents      → instrument_strands_agents()
    mcp                 → instrument_mcp()
    (others: agno, agentspec, agent-framework, beeai, guardrails, instructor,
             monkai-agent, openlit, openllmetry, pipecat, portkey)

  If the framework is not in the list, fall back to the OpenInference instrumentation
  approach instead (see the OpenInference task prompt).

  Add "arthur-observability-sdk[<extra>]" to requirements.txt / pyproject.toml.
  Use "arthur-observability-sdk[all]" if unsure or if multiple frameworks are used.

  In the entry point, add Arthur initialization (after any existing imports):
    from arthur_observability_sdk import Arthur
    import os

    # Arthur raises ValueError if none of task_id / task_name / service_name is given.
    # NOTE: ARTHUR_TASK_ID env var is NOT read automatically — must be passed explicitly.
    # NOTE: ARTHUR_BASE_URL and ARTHUR_API_KEY ARE read automatically from env.
    arthur = Arthur(
        api_key=os.environ.get("ARTHUR_API_KEY"),        # auto-read, but explicit is cleaner
        base_url=os.environ.get("ARTHUR_BASE_URL", "<ARTHUR_ENGINE_URL>"),  # auto-read
        task_id=os.environ.get("ARTHUR_TASK_ID", "<ARTHUR_TASK_ID>"),       # NOT auto-read
        service_name="<app-name>",
        # resource_attributes: arthur.task is set automatically from task_id — don't add it
    )
    arthur.instrument_<framework>()   # call once; patches the framework's HTTP client

  At process exit / application teardown, flush pending spans:
    arthur.shutdown()

PART B — SESSION + USER CONTEXT (CRITICAL — without this each LLM call is a separate trace):

  The preferred way to tag spans with session and user is arthur.attributes(), which
  works as both a context manager and a decorator:

    import uuid
    session_id = <derive from app state, or str(uuid.uuid4())>

    # Context manager form (use around the full request handler body):
    with arthur.attributes(session_id=session_id,
                           user_id=user_id):  # omit this kwarg if not tracking users
        # all existing processing code here — LLM calls are recorded automatically

    # Decorator form:
    @arthur.attributes(session_id=session_id)
    def handle_request(message):
        ...

  Session-only: use arthur.session(session_id) as context manager or decorator.
  User-only:    use arthur.user(user_id)        as context manager or decorator.

  For streaming/generator handlers (yield), use explicit OTel attach/detach because
  Python context managers cannot straddle yield points.
  IMPORTANT: use otel_set_value to store session_id in the OTel context (not just as a
  span attribute) — otherwise child auto-instrumented spans won't inherit session.id:
    from opentelemetry import trace, context as otel_ctx
    from opentelemetry.trace import set_span_in_context
    from opentelemetry.context import set_value as otel_set_value
    from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues

    tracer = trace.get_tracer(__name__)

    def streaming_handler(message, session_id, ...):
        root_span = tracer.start_span("handler_name")
        root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                OpenInferenceSpanKindValues.CHAIN.value)
        root_span.set_attribute(SpanAttributes.INPUT_VALUE, message)
        # Build context with root span as parent AND session_id in OTel context
        # so that all child auto-instrumented spans inherit both correctly:
        ctx = otel_set_value(SpanAttributes.SESSION_ID, session_id,
                             context=set_span_in_context(root_span))
        token = otel_ctx.attach(ctx)
        try:
            for chunk in <inner_generator>:
                otel_ctx.detach(token)
                yield chunk
                token = otel_ctx.attach(ctx)
            root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <final_response>)
        finally:
            root_span.end()
            otel_ctx.detach(token)

  For non-streaming handlers that need a root CHAIN span (e.g., to group multiple LLM
  calls into one trace), add an explicit root span inside the arthur.attributes() block:
    from opentelemetry import trace
    from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
    import json

    tracer = trace.get_tracer(__name__)

    with arthur.attributes(session_id=session_id):
        with tracer.start_as_current_span("<handler_name>") as root_span:
            root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                    OpenInferenceSpanKindValues.CHAIN.value)
            root_span.set_attribute(SpanAttributes.INPUT_VALUE, <user_input>)
            # all existing processing code here
            root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <response>)

PART C — TOOL SPANS (if app uses LLM tool-calling):
  # Uses `tracer` defined in PART B. If not using PART B, add after arthur initialization:
  #   from opentelemetry import trace; tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("<tool_name>") as tool_span:
        tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                OpenInferenceSpanKindValues.TOOL.value)
        tool_span.set_attribute(SpanAttributes.TOOL_NAME, "<tool_name>")
        tool_span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(<tool_input>))
        tool_span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")
        result = <execute_tool(tool_input)>
        output_str = json.dumps(result) if not isinstance(result, str) else result
        tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE, output_str)
        tool_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

PART D — RETRIEVER SPANS (if app does RAG/vector search):
    with tracer.start_as_current_span("retrieval") as ret_span:
        ret_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                               OpenInferenceSpanKindValues.RETRIEVER.value)
        ret_span.set_attribute(SpanAttributes.INPUT_VALUE, <search_query>)
        docs = <execute_retrieval(query)>
        retrieved = []
        for i, doc in enumerate(docs):
            doc_text = <doc_content>
            ret_span.set_attribute(f"retrieval.documents.{i}.document.content", doc_text)
            entry = {"document_content": doc_text}
            if <score_available>:
                score = float(<doc_score>)
                ret_span.set_attribute(f"retrieval.documents.{i}.document.score", score)
                entry["score"] = score
            retrieved.append(entry)
        # REQUIRED: set output.value so retrieved docs appear in Arthur Engine UI
        ret_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(retrieved))

STEP 3 — VALIDATION:
  Install: pip install 'arthur-observability-sdk[<extra>]' (or: uv sync)
  Check: python -c "from arthur_observability_sdk import Arthur; print('import OK')"
  Run existing test suite if present; fix any new failures you introduced.
  Print final JSON result on the last line.
```

---

## Mastra TypeScript Instrumentation Task Prompt

```
You are an expert TypeScript developer. Instrument the Mastra app at: <REPO_PATH>

Arthur Engine URL: <ARTHUR_ENGINE_URL>
Arthur Task ID: <ARTHUR_TASK_ID>

RULES: no hardcoded API keys; add env vars to .env and .env.example; smallest possible changes.
Print final JSON on the last line: {"success":true,"testsPassed":true,"summary":"<one sentence>"}

STEP 1 — Find the Mastra instance file (usually src/mastra/index.ts). Read it fully.
Check if @mastra/arthur is already in package.json dependencies (skip STEP 2 if yes).

STEP 2 — Implementation:

  Install the package:
    npm install @mastra/arthur    # or yarn add / pnpm add

  In the Mastra instance file, add the ArthurExporter to the observability config.

  IMPORTANT — correct import and wiring pattern:
    // Correct import path (note the /mastra subpath):
    import { Mastra } from "@mastra/core/mastra";
    import { ArthurExporter } from "@mastra/arthur";

    export const mastra = new Mastra({
      // ... preserve all existing config (agents, storage, logger, etc.) ...
      observability: {
        configs: {
          arthur: {
            serviceName: "<app-name>",   // descriptive name for this service
            exporters: [
              new ArthurExporter({
                apiKey: process.env.ARTHUR_API_KEY!,
                endpoint: process.env.ARTHUR_BASE_URL ?? "<ARTHUR_ENGINE_URL>",
                taskId: process.env.ARTHUR_TASK_ID,  // optional but recommended
              }),
            ],
          },
        },
      },
    });

  Constructor notes:
  - `endpoint` is the Arthur Engine base URL (e.g. "http://localhost:3030") — NOT the
    full traces path; the exporter appends /api/v1/traces automatically.
  - `apiKey` is added as Authorization: Bearer header automatically.
  - `taskId` is optional; omit if ARTHUR_TASK_ID will always be set in the environment.
  - Zero-config alternative: `new ArthurExporter()` with no args reads ARTHUR_API_KEY
    and ARTHUR_BASE_URL from env automatically (ARTHUR_TASK_ID is also read if set).
  - DO NOT wrap observability in `new Observability(...)` — it is a plain object.
  - DO NOT import from `@mastra/observability` — that package does not exist.

  Add to .env (gitignored):
    ARTHUR_API_KEY=<ARTHUR_API_KEY>
    ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
    ARTHUR_TASK_ID=<ARTHUR_TASK_ID>
  Add placeholder lines to .env.example.

  Optional — trace tagging at call sites (useful for filtering in Arthur UI):
    const result = await agent.generate("Hello", {
      tracingOptions: {
        tags: ["production", "experiment-v2"],
        metadata: { companyId: "acme", tier: "enterprise" },
      },
    });

STEP 3 — Validation:
  Run: npm install (or yarn/pnpm install)
  Run: npx tsc --noEmit
  Run existing tests if present; fix any new failures you introduced.
  Print final JSON result.
```

---

## OpenInference Instrumentation Task Prompt (Python/TypeScript, Other Frameworks)

```
You are an expert developer. Instrument the agentic application at: <REPO_PATH>
using OpenInference / OpenTelemetry for Arthur GenAI Engine.

Arthur Engine URL: <ARTHUR_ENGINE_URL>
Arthur Task ID: <ARTHUR_TASK_ID>

RULES: no hardcoded keys; add env vars to .env and .env.example; smallest possible changes.
Print final JSON: {"success":true,"testsPassed":true,"summary":"<one sentence>"}

--- OPENINFERENCE SPAN KIND REFERENCE ---
Every span MUST have openinference.span.kind set to one of:
  CHAIN     — root entry point or glue between steps (use for the request handler)
  LLM       — a call to an LLM provider (auto-set by instrumentors; set manually if wrapping raw API calls)
  TOOL      — execution of an external tool/function called by an LLM
  RETRIEVER — a data retrieval step (vector store, database, search)
  AGENT     — a reasoning block that acts on tools using LLM guidance
  RERANKER  — reranking a set of retrieved documents
  EMBEDDING — a call to an embedding model
  GUARDRAIL — content filtering / safety check
  EVALUATOR — an evaluation function assessing LLM output quality
  PROMPT    — rendering a prompt template with variable substitution

--- ATTRIBUTE FLATTENING RULE ---
OpenTelemetry span attributes are key-value pairs where values must be scalars.
Lists of objects are flattened with zero-based indexed dot notation:
  List item 0, field "message.role"  → "llm.input_messages.0.message.role"
  List item 1, field "message.content" → "llm.input_messages.1.message.content"
Never pass a list of dicts directly; always flatten.

--- KEY ATTRIBUTE REFERENCE ---
Universal (any span kind):
  input.value           String  — the span's input (plain text or JSON string)
  input.mime_type       String  — "text/plain" or "application/json"
  output.value          String  — the span's output (plain text or JSON string)
  output.mime_type      String  — "text/plain" or "application/json"

Context (propagated to all spans via using_attributes / using_session / using_user):
  session.id            String  — groups all spans from one conversation/request chain
  user.id               String  — identifies the end user
  metadata              String  — JSON string of arbitrary key-value metadata
  tag.tags              List[str] — categories for filtering

LLM spans (openinference.span.kind = LLM):
  llm.system            String  — REQUIRED: AI product e.g. "openai", "anthropic", "cohere"
  llm.model_name        String  — model identifier e.g. "gpt-4o", "claude-3-5-haiku-20241022"
  llm.invocation_parameters  String — JSON of params sent to model (temperature, max_tokens, etc.)
  llm.input_messages.{i}.message.role     String — "system", "user", "assistant", "tool"
  llm.input_messages.{i}.message.content  String — message text
  llm.output_messages.{i}.message.role    String — "assistant"
  llm.output_messages.{i}.message.content String — response text
  llm.output_messages.{i}.message.tool_calls.{j}.tool_call.id              String
  llm.output_messages.{i}.message.tool_calls.{j}.tool_call.function.name   String
  llm.output_messages.{i}.message.tool_calls.{j}.tool_call.function.arguments String (JSON)
  llm.token_count.prompt      Integer
  llm.token_count.completion  Integer
  llm.token_count.total       Integer
  llm.tools.{i}.tool.json_schema  String — JSON schema of tools available to the LLM

Tool spans (openinference.span.kind = TOOL):
  tool.name             String  — name of the tool/function
  tool.description      String  — what the tool does
  tool.parameters       String  — JSON schema of the tool's input parameters
  tool.id               String  — tool_call.id from the LLM response (links call to result)
  input.value           String  — tool input (JSON string of arguments)
  output.value          String  — tool output (JSON string of result)

Retriever spans (openinference.span.kind = RETRIEVER):
  input.value                               String — the search query
  retrieval.documents.{i}.document.content  String — REQUIRED: text of retrieved doc
  retrieval.documents.{i}.document.score    Float  — relevance score
  retrieval.documents.{i}.document.id       String — document identifier
  retrieval.documents.{i}.document.metadata String — JSON metadata about the doc
  output.value  String — REQUIRED: JSON-encoded list of retrieved docs (for Arthur UI)

Tool result messages (role="tool" in next LLM input):
  llm.input_messages.{i}.message.role          = "tool"
  llm.input_messages.{i}.message.content       = result as string
  llm.input_messages.{i}.message.tool_call_id  = matching tool_call.id
  llm.input_messages.{i}.message.name          = function name (optional)
---

STEP 1 — Detect language (Python/TypeScript/JavaScript) and LLM framework.

===== PYTHON IMPLEMENTATION =====

PART A — OTel setup:
  Add to requirements.txt / pyproject.toml:
    opentelemetry-sdk
    opentelemetry-exporter-otlp-proto-http
    openinference-instrumentation-<framework>   # e.g. openai, langchain, anthropic
    openinference-semantic-conventions

  In the entry point:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from openinference.instrumentation.<framework> import <Framework>Instrumentor
    from openinference.instrumentation import using_attributes  # using_session, using_user also available
    from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
    import os, json, uuid

    provider = TracerProvider()
    exporter = OTLPSpanExporter(
        endpoint=f"{os.environ.get('ARTHUR_BASE_URL', '<ARTHUR_ENGINE_URL>')}/api/v1/traces",
        headers={"Authorization": f"Bearer {os.environ.get('ARTHUR_API_KEY', '')}"},
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    <Framework>Instrumentor().instrument()
    tracer = trace.get_tracer(__name__)

PART B — ROOT CHAIN SPAN + SESSION + USER CONTEXT:

  # Non-streaming — context manager form (preferred):
  session_id = <from app state or str(uuid.uuid4())>
  with using_attributes(session_id=session_id,
                        user_id=user_id,  # omit this kwarg if not tracking users
                        metadata=json.dumps(<extra_metadata_dict_or_None>)):
      with tracer.start_as_current_span("<handler_name>") as root_span:
          root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                  OpenInferenceSpanKindValues.CHAIN.value)
          root_span.set_attribute(SpanAttributes.INPUT_VALUE, <user_input>)
          root_span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "text/plain")
          # all existing processing code here
          root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <response>)
          root_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "text/plain")

  # Streaming/generator (yield) — use explicit attach/detach:
  from opentelemetry import context as otel_ctx
  from opentelemetry.trace import set_span_in_context
  from opentelemetry.context import set_value as otel_set_value

  def streaming_handler(message, session_id, ...):
      root_span = tracer.start_span("handler_name")
      root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                              OpenInferenceSpanKindValues.CHAIN.value)
      root_span.set_attribute(SpanAttributes.INPUT_VALUE, message)
      # Store session_id in OTel context so child spans inherit it:
      ctx = otel_set_value(SpanAttributes.SESSION_ID, session_id,
                           context=set_span_in_context(root_span))
      token = otel_ctx.attach(ctx)
      try:
          for chunk in <inner_generator>:
              otel_ctx.detach(token)
              yield chunk
              token = otel_ctx.attach(ctx)
          root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <final_response>)
      finally:
          root_span.end()
          otel_ctx.detach(token)

PART C — TOOL SPANS (when app uses LLM tool-calling):
  with tracer.start_as_current_span("<tool_name>") as tool_span:
      tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                              OpenInferenceSpanKindValues.TOOL.value)
      tool_span.set_attribute(SpanAttributes.TOOL_NAME, "<tool_name>")
      tool_span.set_attribute(SpanAttributes.TOOL_DESCRIPTION, "<what it does>")
      # tool.id links this execution back to the LLM's tool_call.id:
      tool_span.set_attribute("tool.id", <tool_call_id_from_llm_response>)
      tool_span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(<tool_arguments>))
      tool_span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")
      result = <execute_tool(tool_arguments)>
      output_str = json.dumps(result) if not isinstance(result, str) else result
      tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE, output_str)
      tool_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

PART D — RETRIEVER SPANS (when app does RAG/vector search):
  with tracer.start_as_current_span("retrieval") as ret_span:
      ret_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                             OpenInferenceSpanKindValues.RETRIEVER.value)
      ret_span.set_attribute(SpanAttributes.INPUT_VALUE, <search_query>)
      docs = <execute_retrieval(search_query)>
      retrieved = []
      for i, doc in enumerate(docs):
          doc_text = <doc_content>
          ret_span.set_attribute(f"retrieval.documents.{i}.document.content", doc_text)
          entry = {"document_content": doc_text}
          if <doc_id_available>:
              ret_span.set_attribute(f"retrieval.documents.{i}.document.id", str(<doc_id>))
          if <score_available>:
              score = float(<doc_score>)
              ret_span.set_attribute(f"retrieval.documents.{i}.document.score", score)
              entry["score"] = score
          retrieved.append(entry)
      # REQUIRED: Arthur Engine reads output.value to display retrieved docs in UI:
      ret_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(retrieved))
      ret_span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

PART E — MANUAL LLM SPANS (only if the framework has no auto-instrumentor):
  with tracer.start_as_current_span("llm_call") as llm_span:
      llm_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                             OpenInferenceSpanKindValues.LLM.value)
      llm_span.set_attribute("llm.system", "<openai|anthropic|cohere|...>")
      llm_span.set_attribute("llm.model_name", "<model-id>")
      llm_span.set_attribute("llm.invocation_parameters",
                             json.dumps({"temperature": 0.7, "max_tokens": 1024}))
      # Flatten input messages:
      for i, msg in enumerate(messages):
          llm_span.set_attribute(f"llm.input_messages.{i}.message.role", msg["role"])
          llm_span.set_attribute(f"llm.input_messages.{i}.message.content", msg["content"])
      response = <call_llm(messages)>
      llm_span.set_attribute(f"llm.output_messages.0.message.role", "assistant")
      llm_span.set_attribute(f"llm.output_messages.0.message.content", response.text)
      llm_span.set_attribute("llm.token_count.prompt", response.usage.prompt_tokens)
      llm_span.set_attribute("llm.token_count.completion", response.usage.completion_tokens)
      llm_span.set_attribute("llm.token_count.total", response.usage.total_tokens)
      llm_span.set_attribute(SpanAttributes.OUTPUT_VALUE, response.text)

===== TYPESCRIPT / JAVASCRIPT IMPLEMENTATION =====

PART A — Install packages:
  npm install \
    @opentelemetry/sdk-trace-node \
    @opentelemetry/exporter-trace-otlp-proto \
    @opentelemetry/sdk-trace-base \
    @opentelemetry/resources \
    @opentelemetry/semantic-conventions \
    @arizeai/openinference-semantic-conventions

  # Framework auto-instrumentors (install the one that matches):
    @arizeai/openinference-instrumentation-openai
    @arizeai/openinference-instrumentation-langchain
    @arizeai/openinference-instrumentation-anthropic
    @arizeai/openinference-instrumentation-llama-index

PART B — Setup (e.g. in instrumentation.ts or at top of entry point):
  import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
  import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
  import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
  import { Resource } from "@opentelemetry/resources";
  import { trace, context, SpanKind } from "@opentelemetry/api";
  import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";

  const provider = new NodeTracerProvider({
    resource: new Resource({ "service.name": "<app-name>" }),
    spanProcessors: [
      new BatchSpanProcessor(
        new OTLPTraceExporter({
          url: `${process.env.ARTHUR_BASE_URL ?? "<ARTHUR_ENGINE_URL>"}/api/v1/traces`,
          headers: { Authorization: `Bearer ${process.env.ARTHUR_API_KEY}` },
        })
      ),
    ],
  });
  provider.register();

  // Instrument the framework (call once before any LLM calls):
  // import { OpenAIInstrumentation } from "@arizeai/openinference-instrumentation-openai";
  // new OpenAIInstrumentation().manuallyInstrument(openaiModule);

  const tracer = trace.getTracer("<app-name>");

PART C — Root CHAIN span wrapping the request handler:
  async function handleRequest(userInput: string, sessionId: string): Promise<string> {
    const span = tracer.startSpan("handle_request");
    span.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "CHAIN");
    span.setAttribute(SemanticConventions.INPUT_VALUE, userInput);
    span.setAttribute("session.id", sessionId);

    return context.with(trace.setSpan(context.active(), span), async () => {
      try {
        const result = await <existing_handler_logic>(userInput);
        span.setAttribute(SemanticConventions.OUTPUT_VALUE, result);
        return result;
      } catch (err) {
        span.recordException(err as Error);
        throw err;
      } finally {
        span.end();
      }
    });
  }

PART D — Tool spans (TypeScript):
  const toolSpan = tracer.startSpan(toolName);
  toolSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, "TOOL");
  toolSpan.setAttribute(SemanticConventions.TOOL_NAME, toolName);
  toolSpan.setAttribute("tool.id", toolCallId);
  toolSpan.setAttribute(SemanticConventions.INPUT_VALUE, JSON.stringify(toolArgs));
  toolSpan.setAttribute(SemanticConventions.INPUT_MIME_TYPE, "application/json");
  try {
    const result = await executeTool(toolArgs);
    toolSpan.setAttribute(SemanticConventions.OUTPUT_VALUE, JSON.stringify(result));
    toolSpan.setAttribute(SemanticConventions.OUTPUT_MIME_TYPE, "application/json");
    return result;
  } finally {
    toolSpan.end();
  }

STEP 3 — Add to .env and .env.example:
  ARTHUR_API_KEY=<ARTHUR_API_KEY>
  ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
  ARTHUR_TASK_ID=<ARTHUR_TASK_ID>

STEP 4 — Install deps, run import/type check, run existing tests if present,
fix any new failures you introduced, print final JSON result.
```

---

## After Sub-agent Completes

- Show the user a summary of changes
- If `"success": false`: warn the user to review changes manually
- If tests failed: note it may be pre-existing failures unrelated to the instrumentation
