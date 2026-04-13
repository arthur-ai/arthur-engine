import { query } from '@anthropic-ai/claude-agent-sdk';
import ora from 'ora';
import chalk from 'chalk';
import { buzzSay } from '../ui/prompts.js';

export interface InstrumentationRequest {
  repoPath: string;
  type: 'python-arthur-sdk' | 'mastra-arthur-exporter' | 'openinference';
  arthurEngineUrl: string;
  taskId: string;
  apiKey: string;
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
    ARTHUR_API_KEY=${req.apiKey}
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
  - Add "arthur-observability-sdk[<framework>]" to requirements.txt / pyproject.toml
    where <framework> matches the detected LLM framework (e.g. langchain, openai, anthropic, crewai)
  - In the entry point, add:
      from arthur_observability_sdk import Arthur
      task_id = os.environ.get("ARTHUR_TASK_ID", "${req.taskId}")
      arthur = Arthur(
          api_key=os.environ.get("ARTHUR_API_KEY"),
          base_url=os.environ.get("ARTHUR_BASE_URL", "${req.arthurEngineUrl}"),
          task_id=task_id,
          service_name="<app-name>",
          resource_attributes={"arthur.task": task_id},
      )
  - Call arthur.instrument_<framework>() matching the detected LLM framework
  - Wrap the main execution with arthur.attributes() context manager if applicable
  - Add to .env (create if needed, ensure .env is in .gitignore):
      ARTHUR_API_KEY=${req.apiKey}
  - Add to .env.example: ARTHUR_API_KEY=your-api-key-here

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
    ARTHUR_API_KEY=${req.apiKey}
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
    Add to requirements.txt:
      opentelemetry-sdk
      opentelemetry-exporter-otlp-proto-http
      openinference-instrumentation-<framework>  (e.g., openinference-instrumentation-langchain)

    In the entry point:
      from opentelemetry import trace
      from opentelemetry.sdk.trace import TracerProvider
      from opentelemetry.sdk.trace.export import BatchSpanProcessor
      from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
      from openinference.instrumentation.<framework> import <Framework>Instrumentor

      provider = TracerProvider()
      exporter = OTLPSpanExporter(
          endpoint="${req.arthurEngineUrl}/api/v1/traces",
          headers={"Authorization": f"Bearer {os.environ.get('ARTHUR_API_KEY', '')}"},
      )
      provider.add_span_processor(BatchSpanProcessor(exporter))
      trace.set_tracer_provider(provider)
      <Framework>Instrumentor().instrument()

  For TypeScript/JavaScript:
    Follow the pattern from the customer-support-agent example, creating an OTLP exporter
    pointing to ${req.arthurEngineUrl}/api/v1/traces with Bearer auth.

  Add to .env (create if needed, ensure .env is in .gitignore):
    ARTHUR_BASE_URL=${req.arthurEngineUrl}
    ARTHUR_API_KEY=${req.apiKey}
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
  onProgress: (msg: string) => void,
): Promise<InstrumentationResult> {
  const spinner = ora({ text: buzzSay('Analyzing codebase and applying instrumentation...'), color: 'cyan' }).start();

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
            // Show last meaningful line to user
            const lastLine = block.text.split('\n').filter(Boolean).at(-1);
            if (lastLine) {
              spinner.text = buzzSay(lastLine.slice(0, 80));
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

/** Display Claude's progress output inline (strips ANSI, truncates long lines) */
export function makeProgressHandler(): (msg: string) => void {
  return (msg: string) => {
    const clean = msg.replace(/\x1B\[[0-9;]*m/g, '').trim();
    if (clean && clean.length < 200) {
      process.stdout.write(chalk.dim('  › ') + clean + '\n');
    }
  };
}
