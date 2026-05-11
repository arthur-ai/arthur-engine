import { query } from '@anthropic-ai/claude-agent-sdk';
import ora from 'ora';
import chalk from 'chalk';
import { buzzSay } from '../ui/prompts.js';

export interface InstrumentationRequest {
  repoPath: string;
  type: 'python-arthur-sdk' | 'mastra-arthur-exporter' | 'openinference';
  arthurEngineUrl: string;
  taskId: string;
}

export interface InstrumentationResult {
  success: boolean;
  testsPassed: boolean;
  summary: string;
}

const SYSTEM_PROMPTS: Record<InstrumentationRequest['type'], string> = {
  'python-arthur-sdk':
    'You are an expert Python developer instrumenting AI/LLM applications with OpenTelemetry-based observability. You write clean, idiomatic Python code.',
  'mastra-arthur-exporter':
    'You are an expert TypeScript developer instrumenting Mastra AI agent applications with OpenTelemetry tracing. You write clean, idiomatic TypeScript.',
  openinference:
    'You are an expert developer instrumenting AI agent applications with OpenTelemetry and OpenInference. You adapt to the framework in use (Python or TypeScript).',
};

function buildPrompt(req: InstrumentationRequest): string {
  const base = `
Arthur Engine URL: ${req.arthurEngineUrl}
Arthur Task ID: ${req.taskId}

IMPORTANT RULES:
- Do NOT hardcode API keys in source code. Always read from environment variables (ARTHUR_API_KEY).
- Add these entries to .env (create if it does not exist; ensure .env is in .gitignore):
    ARTHUR_API_KEY=$ARTHUR_API_KEY
    ARTHUR_BASE_URL=${req.arthurEngineUrl}
    ARTHUR_TASK_ID=${req.taskId}
- Also add placeholder entries to .env.example:
    ARTHUR_API_KEY=your-api-key-here
    ARTHUR_BASE_URL=${req.arthurEngineUrl}
    ARTHUR_TASK_ID=${req.taskId}
- Make the smallest possible changes — instrument, don't refactor.
- The task is complete only when:
  1. All dependencies are installed (pip install or npm install).
  2. An import/syntax check passes (python -c "import <module>" or tsc --noEmit).
  3. The existing test suite runs (if one exists). Fix any NEW test failures you introduced.
  4. You print a final JSON result block on the last line of your output.

FINAL OUTPUT FORMAT (print this exact JSON on the last line):
{"success":true,"testsPassed":true,"summary":"<one sentence>"}
or
{"success":false,"testsPassed":false,"summary":"<what went wrong>"}
`;

  const typePrompts: Record<InstrumentationRequest['type'], string> = {
    'python-arthur-sdk': `
Instrument this Python agentic application with the Arthur Python Observability SDK.

Reference SDK: https://github.com/arthur-ai/arthur-engine/tree/main/arthur-observability-sdk

Plan ultrathink — carefully examine all files first, then implement:

STEP 1 — ANALYSIS:
  - List all files to understand the project structure
  - Read requirements.txt / pyproject.toml to see current dependencies and note the package manager (uv/pip/poetry)
  - Find the application entry point (main.py, app.py, __main__.py, or similar)
  - Identify the LLM framework used (openai, langchain, anthropic, crewai, etc.)
  - Check if arthur_observability_sdk is already installed (skip if yes)

STEP 2 — IMPLEMENTATION (only if not already instrumented):

PART A — SDK SETUP (always required):
  - Add "arthur-observability-sdk[<framework>]" to requirements.txt / pyproject.toml
    where <framework> matches the detected LLM framework (e.g. langchain, openai, anthropic, crewai)
  - In the entry point, add:
      from arthur_observability_sdk import Arthur
      import os
      task_id = os.environ.get("ARTHUR_TASK_ID", "${req.taskId}")
      arthur = Arthur(
          api_key=os.environ.get("ARTHUR_API_KEY"),
          base_url=os.environ.get("ARTHUR_BASE_URL", "${req.arthurEngineUrl}"),
          task_id=task_id,
          service_name="<app-name>",
          resource_attributes={"arthur.task": task_id},
      )
  - Call arthur.instrument_<framework>() to auto-instrument all LLM API calls
  - Add to .env (create if needed, ensure .env is in .gitignore):
      ARTHUR_API_KEY=$ARTHUR_API_KEY
  - Add to .env.example: ARTHUR_API_KEY=your-api-key-here

PART B — ROOT SPAN + SESSION ID (CRITICAL — without this, each LLM call is a SEPARATE trace):
  The auto-instrumentor creates one span per LLM call. Without a parent span to connect them,
  one user interaction emits multiple disconnected traces. A root CHAIN span fixes this.

  Add these imports near the top of the file where arthur is initialised (or in a shared module):
      from opentelemetry import trace
      from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
      import json, uuid
      tracer = trace.get_tracer(__name__)

  Find the main request handler — the function/method that processes one complete user message
  end-to-end (e.g. a Gradio/FastAPI/Flask chat handler, a process() / answer() / run() method).

  Wrap its body with a root CHAIN span AND a session context manager:
      # Derive session_id from app state: look for existing session key, conversation ID,
      # user ID, or generate one: str(uuid.uuid4())
      session_id = <session_id>
      with arthur.session(session_id):
          with tracer.start_as_current_span("<handler_name>") as root_span:
              root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                      OpenInferenceSpanKindValues.CHAIN.value)
              root_span.set_attribute(SpanAttributes.INPUT_VALUE, <user_input_message>)
              # all existing processing code runs here; every sub-span becomes a child
              root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <final_response_text>)

  IMPORTANT — streaming / generator handlers: Python async frameworks (Gradio, FastAPI, etc.)
  may resume a generator in a different async task or thread, which resets the OTel context
  between iterations. A context-manager-based span (with tracer.start_as_current_span) WILL
  lose its parent context across yield points. Use explicit attach/detach instead:

      from opentelemetry import context as otel_ctx
      from opentelemetry.trace import set_span_in_context
      from opentelemetry.context import set_value as otel_set_value

      def handler(message, ...):
          yield <initial_update>          # yield BEFORE creating span (fine)

          root_span = tracer.start_span("handler_name")
          root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                  OpenInferenceSpanKindValues.CHAIN.value)
          root_span.set_attribute(SpanAttributes.INPUT_VALUE, message)

          span_ctx = set_span_in_context(
              root_span,
              otel_set_value(SpanAttributes.SESSION_ID, session_id),
          )
          token = otel_ctx.attach(span_ctx)
          try:
              for chunk in <inner_generator>:
                  <process chunk>
                  otel_ctx.detach(token)
                  yield <chunk_to_caller>
                  token = otel_ctx.attach(span_ctx)  # re-attach after each yield
              root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <final_response>)
          finally:
              root_span.end()
              otel_ctx.detach(token)

PART C — TOOL SPANS (for LLM tool-calling patterns):
  If the application uses LLM tool calling — i.e. the LLM outputs tool-call parameters and
  then Python code executes the actual function — wrap each tool execution with a TOOL span:
      with tracer.start_as_current_span("<tool_name>") as tool_span:
          tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                  OpenInferenceSpanKindValues.TOOL.value)
          tool_span.set_attribute(SpanAttributes.TOOL_NAME, "<tool_name>")
          tool_span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(<tool_input_params>))
          result = <execute_tool(tool_input_params)>
          tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE,
                                  json.dumps(result) if not isinstance(result, str) else result)

PART D — RETRIEVAL SPANS (for RAG / search patterns):
  If the application performs retrieval (vector search, semantic search, full-text search,
  document lookup), wrap the retrieval call with a RETRIEVER span. You MUST set BOTH:
    (a) per-document attributes so Arthur can index individual docs, AND
    (b) output.value as a JSON list so Arthur Engine displays the retrieved context — without
        output.value the retrieval output panel will appear empty in the UI.

      with tracer.start_as_current_span("retrieval") as ret_span:
          ret_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                 OpenInferenceSpanKindValues.RETRIEVER.value)
          ret_span.set_attribute(SpanAttributes.INPUT_VALUE, <search_query_string>)
          docs = <execute_retrieval(search_query)>
          retrieved = []
          for i, doc in enumerate(docs):
              doc_text = <doc_text_content>
              ret_span.set_attribute(f"retrieval.documents.{i}.document.content", doc_text)
              entry = {"document_content": doc_text}
              # Include score if the retrieval API returns one (float 0–1 preferred)
              if <score_available>:
                  score = float(<doc_score>)
                  ret_span.set_attribute(f"retrieval.documents.{i}.document.score", score)
                  entry["score"] = score
              retrieved.append(entry)
          # REQUIRED: set output.value so the retrieval output is visible in Arthur Engine
          ret_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(retrieved))

STEP 3 — VALIDATION:
  - Run: pip install 'arthur-observability-sdk[<framework>]'
    (or: uv sync if using uv)
  - Run: python -c "from arthur_observability_sdk import Arthur; print('import OK')"
  - Run the existing test suite if present (pytest, python -m pytest, or similar)
  - Fix any new test failures you introduced
  - Print the final JSON result

${base}`,

    'mastra-arthur-exporter': `
Instrument this Mastra TypeScript application with the Arthur observability exporter.

Reference: https://mastra.ai/docs/observability/tracing/exporters/arthur

Plan ultrathink — carefully examine all files first, then implement:

STEP 1 — ANALYSIS:
  - List all files to understand the project structure
  - Read package.json to see current dependencies
  - Find the Mastra instance initialization file (usually src/mastra/index.ts)
  - Check if @mastra/arthur is already installed and ArthurExporter is already registered (skip if yes)

STEP 2 — IMPLEMENTATION (only if not already instrumented):
  Install the published Arthur exporter package:
    npm install @mastra/arthur

  Import and register in the Mastra instance initialization file:
    import { Mastra } from '@mastra/core'
    import { Observability } from '@mastra/observability'
    import { ArthurExporter } from '@mastra/arthur'

    export const mastra = new Mastra({
      observability: new Observability({
        configs: {
          arthur: {
            serviceName: '<app-name>',
            exporters: [new ArthurExporter()],
          },
        },
      }),
    })

  The ArthurExporter reads these env vars automatically (no constructor args needed):
    ARTHUR_API_KEY   — required
    ARTHUR_BASE_URL  — required (set to ${req.arthurEngineUrl})
    ARTHUR_TASK_ID   — optional (set to ${req.taskId})

  Add to .env (create if needed, ensure .env is in .gitignore):
    ARTHUR_BASE_URL=${req.arthurEngineUrl}
    ARTHUR_API_KEY=$ARTHUR_API_KEY
    ARTHUR_TASK_ID=${req.taskId}
  Add to .env.example:
    ARTHUR_BASE_URL=${req.arthurEngineUrl}
    ARTHUR_API_KEY=your-api-key-here
    ARTHUR_TASK_ID=${req.taskId}

STEP 3 — VALIDATION:
  - Run: npm install (or yarn install / pnpm install)
  - Run: npx tsc --noEmit
  - Run the existing test suite if present (npm test, vitest run, or similar)
  - Fix any new test failures you introduced
  - Print the final JSON result

${base}`,

    openinference: `
Instrument this agentic application with OpenInference / OpenTelemetry for Arthur GenAI Engine.

Reference examples: https://github.com/arthur-ai/arthur-engine/tree/dev/genai-engine/examples/agents

Plan ultrathink — carefully examine all files first, then implement:

STEP 1 — ANALYSIS:
  - List all files to understand project structure and language
  - Read dependency manifests (requirements.txt, package.json, pyproject.toml)
  - Find the entry point and identify the LLM framework (LangChain, OpenAI, CrewAI, etc.)
  - Check if OpenInference / OpenTelemetry is already configured (skip if yes)

STEP 2 — IMPLEMENTATION (only if not already instrumented):

  For Python:
    PART A — OTel + framework instrumentor setup:
      Add to requirements.txt:
        opentelemetry-sdk
        opentelemetry-exporter-otlp-proto-http
        openinference-instrumentation-<framework>  (e.g., openinference-instrumentation-langchain)
        openinference-semantic-conventions

      In the entry point:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from openinference.instrumentation.<framework> import <Framework>Instrumentor
        from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
        import os, json, uuid

        provider = TracerProvider()
        exporter = OTLPSpanExporter(
            endpoint="${req.arthurEngineUrl}/api/v1/traces",
            headers={"Authorization": f"Bearer {os.environ.get('ARTHUR_API_KEY', '')}"},
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        <Framework>Instrumentor().instrument()
        tracer = trace.get_tracer(__name__)

    PART B — ROOT SPAN + SESSION ID (CRITICAL — without this, each LLM call is a SEPARATE trace):
      The auto-instrumentor creates one span per LLM call; without a parent span every call
      becomes its own trace. A root CHAIN span fixes this.

      Find the main request handler — the function/method that processes one complete user
      message end-to-end (e.g. a Gradio/FastAPI/Flask chat handler, a process() / answer() /
      run() / invoke() method).

      Wrap its body with a root CHAIN span AND a session context manager. Use
      using_session from openinference.instrumentation:
          from openinference.instrumentation import using_session

          session_id = <get from app state: session key, conversation ID, or str(uuid.uuid4())>
          with using_session(session_id=session_id):
              with tracer.start_as_current_span("<handler_name>") as root_span:
                  root_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                          OpenInferenceSpanKindValues.CHAIN.value)
                  root_span.set_attribute(SpanAttributes.INPUT_VALUE, <user_input_message>)
                  # all existing processing code runs here
                  root_span.set_attribute(SpanAttributes.OUTPUT_VALUE, <final_response_text>)

      If the handler is a streaming/generator function (uses yield), the session + root span
      must wrap the generator CONSUMPTION in the caller so spans stay open during streaming.

    PART C — TOOL SPANS (for LLM tool-calling patterns):
      If the application uses LLM tool calling (the LLM outputs tool-call params and then Python
      code executes the actual function), wrap each tool execution:
          with tracer.start_as_current_span("<tool_name>") as tool_span:
              tool_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                      OpenInferenceSpanKindValues.TOOL.value)
              tool_span.set_attribute(SpanAttributes.TOOL_NAME, "<tool_name>")
              tool_span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(<tool_input_params>))
              result = <execute_tool(tool_input_params)>
              tool_span.set_attribute(SpanAttributes.OUTPUT_VALUE,
                                      json.dumps(result) if not isinstance(result, str) else result)

    PART D — RETRIEVAL SPANS (for RAG / search patterns):
      If the application performs retrieval (vector search, semantic search, document lookup),
      wrap the retrieval call with a RETRIEVER span. You MUST set BOTH per-document attributes
      AND output.value as a JSON list — without output.value, Arthur Engine shows empty output:
          with tracer.start_as_current_span("retrieval") as ret_span:
              ret_span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND,
                                     OpenInferenceSpanKindValues.RETRIEVER.value)
              ret_span.set_attribute(SpanAttributes.INPUT_VALUE, <search_query_string>)
              docs = <execute_retrieval(search_query)>
              retrieved = []
              for i, doc in enumerate(docs):
                  doc_text = <doc_text_content>
                  ret_span.set_attribute(f"retrieval.documents.{i}.document.content", doc_text)
                  entry = {"document_content": doc_text}
                  if <score_available>:
                      score = float(<doc_score>)
                      ret_span.set_attribute(f"retrieval.documents.{i}.document.score", score)
                      entry["score"] = score
                  retrieved.append(entry)
              # REQUIRED: set output.value so retrieved docs are visible in Arthur Engine
              ret_span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(retrieved))

  For TypeScript/JavaScript:
    Follow the pattern from the customer-support-agent example, creating an OTLP exporter
    pointing to ${req.arthurEngineUrl}/api/v1/traces with Bearer auth.
    Also add a root span around the request handler (same concept as Python PART B above).

  Add to .env (create if needed, ensure .env is in .gitignore):
    ARTHUR_BASE_URL=${req.arthurEngineUrl}
    ARTHUR_API_KEY=$ARTHUR_API_KEY
    ARTHUR_TASK_ID=${req.taskId}
  Add to .env.example:
    ARTHUR_BASE_URL=${req.arthurEngineUrl}
    ARTHUR_API_KEY=your-api-key-here
    ARTHUR_TASK_ID=${req.taskId}

STEP 3 — VALIDATION:
  - Install new dependencies
  - Run an import/syntax check
  - Run the existing test suite if present and fix any new failures
  - Print the final JSON result

${base}`,
  };

  return typePrompts[req.type];
}

function parseResult(text: string): InstrumentationResult {
  // Look for the final JSON result line
  const lines = text.split('\n').reverse();
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('{') && trimmed.includes('"success"')) {
      try {
        return JSON.parse(trimmed) as InstrumentationResult;
      } catch { /* try next line */ }
    }
  }
  // If no JSON found, infer from text
  const failed = /error|fail|exception|traceback/i.test(text.slice(-500));
  return {
    success: !failed,
    testsPassed: !failed,
    summary: failed ? 'Instrumentation may have issues (no structured result returned)' : 'Instrumentation applied',
  };
}

export async function instrumentCodeWithClaude(
  req: InstrumentationRequest,
): Promise<InstrumentationResult> {
  const spinner = ora({ text: buzzSay('Analyzing codebase and applying instrumentation...'), color: 'cyan' }).start();

  // Progress handler with access to spinner so it can clear the spinner line
  // before writing — this prevents progress text from being appended to the
  // spinner's line (a collision caused by ora's \r-based rendering).
  const onProgress = (msg: string) => {
    const clean = msg.replace(/\x1B\[[0-9;]*m/g, '').trim();
    if (clean) {
      spinner.clear(); // Erase spinner from current line; cursor stays at line start
      process.stdout.write(chalk.dim('  › ') + clean + '\n');
      // ora redraws the spinner on the next timer tick at the new cursor position
    }
  };

  let fullOutput = '';
  let finalResult: InstrumentationResult | null = null;

  try {
    const stream = query({
      prompt: buildPrompt(req),
      options: {
        cwd: req.repoPath,
        // Full tool access so Claude can run tests, install deps, fix failures
        allowedTools: ['Read', 'Glob', 'Grep', 'Edit', 'Write', 'Bash'],
        permissionMode: 'acceptEdits',
        systemPrompt: SYSTEM_PROMPTS[req.type],
      },
    });

    for await (const message of stream) {
      if (message.type === 'assistant') {
        const content = (message as { type: 'assistant'; message: { content: Array<{ type: string; text?: string }> } }).message?.content ?? [];
        for (const block of content) {
          if (block.type === 'text' && block.text) {
            fullOutput += block.text;
            // Show last meaningful line to user (no spinner.text update — avoids
            // duplicating the same content in both spinner and progress line)
            const lastLine = block.text.split('\n').filter(Boolean).at(-1);
            if (lastLine) {
              onProgress(lastLine);
            }
          }
        }
      } else if (message.type === 'result') {
        const resultMsg = message as { type: 'result'; result: string; subtype: string };
        finalResult = parseResult(fullOutput + '\n' + (resultMsg.result ?? ''));

        if (resultMsg.subtype === 'success') {
          spinner.succeed(buzzSay('Instrumentation task completed.'));
        } else {
          spinner.fail(buzzSay(`Task ended: ${resultMsg.subtype}`));
          if (!finalResult.success) {
            finalResult.success = false;
          }
        }
      }
    }
  } catch (err) {
    spinner.fail(buzzSay('Instrumentation failed.'));
    const errMsg = err instanceof Error ? err.message : String(err);
    return { success: false, testsPassed: false, summary: errMsg };
  }

  return finalResult ?? parseResult(fullOutput);
}
