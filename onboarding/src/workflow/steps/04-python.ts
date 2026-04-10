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
 * Step 4: Python instrumentation.
 * Returns true if this step handled the repo (either already instrumented, user declined, or we instrumented it).
 * Returns false if the repo is not a Python application → try next step.
 */
export async function step4_InstrumentPython(state: WorkflowState): Promise<boolean> {
  const analysis = state.analysis!;

  // 1. Is this a Python application?
  if (analysis.language !== 'python') {
    p.log.info(buzzSay(`Repository detected as ${analysis.language} — skipping Python instrumentation.`));
    return false;
  }

  logSuccess(`Python application detected. Framework: ${analysis.framework ?? 'unknown'}`);

  // 2. Already instrumented?
  if (analysis.isInstrumented && analysis.instrumentationType === 'arthur-sdk') {
    logSuccess('Arthur Python Observability SDK is already instrumented. All systems go.');
    return true;
  }

  if (analysis.isInstrumented) {
    logSuccess(`Application is already instrumented (${analysis.instrumentationType}). Proceeding.`);
    return true;
  }

  // 3. Ask permission to instrument
  note(
    'Buzz will add the Arthur Python Observability SDK to your application.\n\n' +
    'What will change:\n' +
    '  • arthur-observability-sdk added to requirements.txt / pyproject.toml\n' +
    '  • Arthur initialization code added to your entry point\n' +
    '  • ARTHUR_API_KEY added to .env.example\n\n' +
    `Arthur Engine URL: ${state.engineUrl}\nTask ID: ${state.taskId}`,
    'Instrumentation plan',
  );

  const approved = await confirm('May Buzz instrument your Python app with the Arthur SDK?');
  if (!approved) {
    logSuccess('Instrumentation skipped by user request.');
    return true; // User declined — handled, skip to verify
  }

  // 4. Set ARTHUR_API_KEY in current process env so Claude can use it
  if (state.apiKey) {
    process.env.ARTHUR_API_KEY = state.apiKey;
    process.env.ARTHUR_BASE_URL = state.engineUrl!;
    process.env.ARTHUR_TASK_ID = state.taskId!;
  }

  p.log.info(buzzSay('Initiating Python instrumentation launch sequence...'));
  console.log();

  const result = await instrumentCodeWithClaude(
    {
      repoPath: state.repoPath,
      type: 'python-arthur-sdk',
      arthurEngineUrl: state.engineUrl!,
      taskId: state.taskId!,
    },
    makeProgressHandler(),
  );

  console.log();

  if (result.success) {
    logSuccess(`Instrumentation applied. ${result.summary}`);
  } else {
    logWarn(`Instrumentation may be incomplete. ${result.summary}`);
    note(
      'Review the changes Claude made and verify manually before proceeding.',
      'Manual verification needed',
    );
  }

  if (!result.testsPassed && result.success) {
    logWarn('Some tests are not passing. This may be pre-existing failures unrelated to Buzz.');
    note(result.summary, 'Test results');
  }

  return true;
}
