import {
  p,
  buzzSay,
  logSuccess,
  logWarn,
  note,
  confirm,
} from '../../ui/prompts.js';
import { instrumentCodeWithClaude } from '../../claude-code/sdk.js';
import type { WorkflowState } from '../orchestrator.js';

/**
 * Step 5: Mastra TypeScript instrumentation.
 * Returns true if handled, false if not a Mastra app.
 */
export async function step5_InstrumentMastra(state: WorkflowState): Promise<boolean> {
  const analysis = state.analysis!;

  // 1. Is this a Mastra app?
  if (analysis.framework !== 'mastra') {
    p.log.info(buzzSay(`Framework detected as "${analysis.framework ?? 'unknown'}" — skipping Mastra instrumentation.`));
    return false;
  }

  logSuccess(`Mastra TypeScript application detected.`);

  // 2. Already instrumented with Mastra Arthur exporter?
  if (analysis.isInstrumented && analysis.instrumentationType === 'mastra-arthur-exporter') {
    logSuccess('Mastra Arthur exporter is already configured. All systems go.');
    return true;
  }

  if (analysis.isInstrumented) {
    logSuccess(`Application is already instrumented (${analysis.instrumentationType}). Proceeding.`);
    return true;
  }

  // 3. Ask permission
  note(
    'Buzz will add the Mastra Arthur exporter to your application.\n\n' +
    'What will change:\n' +
    '  • @mastra/arthur package installed (npm install @mastra/arthur)\n' +
    '  • ArthurExporter registered in your Mastra instance observability config\n' +
    '  • ARTHUR_BASE_URL, ARTHUR_API_KEY, ARTHUR_TASK_ID added to .env (with actual values) and .env.example (placeholders)\n\n' +
    `Arthur Engine URL: ${state.engineUrl}\nTask ID: ${state.taskId}`,
    'Instrumentation plan',
  );

  const approved = await confirm('May Buzz add the Mastra Arthur exporter to your application?');
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

  p.log.info(buzzSay('Initiating Mastra Arthur exporter launch sequence...'));
  console.log();

  const result = await instrumentCodeWithClaude(
    {
      repoPath: state.repoPath,
      type: 'mastra-arthur-exporter',
      arthurEngineUrl: state.engineUrl!,
      taskId: state.taskId!,
      apiKey: state.apiKey!,
    },
  );

  console.log();

  if (result.success) {
    logSuccess(`Mastra exporter configured. ${result.summary}`);
  } else {
    logWarn(`Instrumentation may be incomplete. ${result.summary}`);
    note(
      'Review the changes Claude made and verify manually before proceeding.',
      'Manual verification needed',
    );
  }

  if (!result.testsPassed && result.success) {
    logWarn('Some tests are not passing. This may be pre-existing failures.');
    note(result.summary, 'Test results');
  }

  return true;
}
