import {
  p,
  buzzSay,
  logSuccess,
  logWarn,
  note,
  confirm,
} from '../../ui/prompts.js';
import { instrumentCodeWithClaude, makeProgressHandler } from '../../claude-code/sdk.js';
import type { WorkflowState } from '../orchestrator.js';

/**
 * Step 6: Instrument any agentic application not covered by steps 4 or 5.
 * Uses OpenInference / OpenTelemetry approach.
 * Always returns true (this is the catch-all step).
 */
export async function step6_InstrumentOther(state: WorkflowState): Promise<boolean> {
  const analysis = state.analysis!;

  p.log.info(
    buzzSay(
      `Detected: ${analysis.language} application${analysis.framework ? ` (${analysis.framework})` : ''}. ` +
      'Applying OpenInference instrumentation.',
    ),
  );

  // Already instrumented with OpenInference?
  if (analysis.isInstrumented && analysis.instrumentationType === 'openinference') {
    logSuccess('OpenInference instrumentation is already configured. All systems go.');
    return true;
  }

  if (analysis.isInstrumented) {
    logSuccess(`Application is already instrumented (${analysis.instrumentationType}). Proceeding.`);
    return true;
  }

  // Ask permission
  note(
    'Buzz will instrument your application with OpenInference and OpenTelemetry for Arthur.\n\n' +
    'What will change:\n' +
    '  • OpenTelemetry OTLP exporter configured to send traces to Arthur\n' +
    '  • OpenInference instrumentor added for your detected LLM framework\n' +
    '  • ARTHUR_BASE_URL, ARTHUR_API_KEY, ARTHUR_TASK_ID added to .env (with actual values) and .env.example (placeholders)\n\n' +
    `Arthur Engine URL: ${state.engineUrl}\nTask ID: ${state.taskId}\n\n` +
    'Reference: github.com/arthur-ai/arthur-engine/tree/dev/genai-engine/examples/agents',
    'Instrumentation plan (OpenInference)',
  );

  const approved = await confirm('May Buzz instrument your application with OpenInference for Arthur?');
  if (!approved) {
    logSuccess('Instrumentation skipped by user request.');
    return true;
  }

  // Set env vars for Claude
  if (state.apiKey) {
    process.env.ARTHUR_API_KEY = state.apiKey;
    process.env.ARTHUR_BASE_URL = state.engineUrl!;
    process.env.ARTHUR_TASK_ID = state.taskId!;
  }

  p.log.info(buzzSay('Initiating OpenInference instrumentation launch sequence...'));
  console.log();

  const result = await instrumentCodeWithClaude(
    {
      repoPath: state.repoPath,
      type: 'openinference',
      arthurEngineUrl: state.engineUrl!,
      taskId: state.taskId!,
      apiKey: state.apiKey!,
    },
    makeProgressHandler(),
  );

  console.log();

  if (result.success) {
    logSuccess(`OpenInference instrumentation applied. ${result.summary}`);
  } else {
    logWarn(`Instrumentation may be incomplete. ${result.summary}`);
    note(
      'Review the changes Claude made and verify manually.\n' +
      'You can also consult the examples at:\n' +
      'github.com/arthur-ai/arthur-engine/tree/dev/genai-engine/examples/agents',
      'Manual verification needed',
    );
  }

  if (!result.testsPassed && result.success) {
    logWarn('Some tests are not passing. This may be pre-existing failures.');
    note(result.summary, 'Test results');
  }

  return true;
}
