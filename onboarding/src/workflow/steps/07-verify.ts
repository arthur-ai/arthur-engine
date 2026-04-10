import ora from 'ora';
import {
  p,
  buzzSay,
  logSuccess,
  logWarn,
  note,
  confirm,
} from '../../ui/prompts.js';
import { ArthurEngineClient } from '../../arthur/client.js';
import { readGenaiEngineConfig, GENAI_ENGINE_ENV_PATH } from '../../config/env.js';
import type { WorkflowState } from '../orchestrator.js';

const POLL_INTERVAL_MS = 3_000;
const POLL_MAX_MS = 60_000;

async function pollForTraces(client: ArthurEngineClient, taskId: string): Promise<boolean> {
  const spinner = ora({ text: buzzSay('Checking for traces in Arthur...'), color: 'cyan' }).start();
  const start = Date.now();

  while (Date.now() - start < POLL_MAX_MS) {
    const traces = await client.getTraces(taskId);
    if (traces.length > 0) {
      spinner.succeed(buzzSay(`We have signal! ${traces.length} trace(s) detected.`));
      return true;
    }
    await new Promise<void>(r => setTimeout(r, POLL_INTERVAL_MS));
    spinner.text = buzzSay(`Scanning for traces... (${Math.round((Date.now() - start) / 1000)}s)`);
  }

  spinner.fail(buzzSay('No traces detected after 60 seconds.'));
  return false;
}

export async function step7_VerifyInstrumentation(state: WorkflowState): Promise<void> {
  const client = new ArthurEngineClient(state.engineUrl!, state.apiKey!);
  const isLocal = state.engineUrl?.includes('localhost') || state.engineUrl?.includes('127.0.0.1');

  note(
    'To verify instrumentation, run your agentic application now so it sends traces to Arthur.\n\n' +
    'Make sure to set these environment variables before running:\n' +
    `  ARTHUR_API_KEY=<your-api-key>\n` +
    `  ARTHUR_BASE_URL=${state.engineUrl}\n` +
    `  ARTHUR_TASK_ID=${state.taskId}`,
    'Run your agent',
  );

  const ready = await confirm('Press Enter / confirm when your agent has run at least once');
  if (!ready) {
    // User cancelled
    return;
  }

  // Poll for traces
  const traced = await pollForTraces(client, state.taskId!);

  if (traced) {
    // Success!
    const apiKeyHint = isLocal
      ? `\n\nAPI key hint (local install):\n  cat ${GENAI_ENGINE_ENV_PATH} | grep GENAI_ENGINE_ADMIN_KEY`
      : '';

    note(
      `Login to Arthur GenAI Engine at:\n  ${state.engineUrl}\n\n` +
      `Your Task ID: ${state.taskId}${apiKeyHint}`,
      'Arthur GenAI Engine is ready',
    );

    logSuccess('Instrumentation confirmed. Your traces are flowing to Arthur.');
  } else {
    // No traces found — give guidance
    logWarn('No traces detected. Instrumentation may not be sending data yet.');

    note(
      'Troubleshooting checklist:\n' +
      '  1. Did your application run and make at least one LLM call?\n' +
      '  2. Is ARTHUR_API_KEY set correctly in your environment?\n' +
      '  3. Is ARTHUR_BASE_URL pointing to: ' + state.engineUrl + '?\n' +
      '  4. Is ARTHUR_TASK_ID set to: ' + state.taskId + '?\n' +
      '  5. Check your application logs for any OpenTelemetry export errors.',
      'No traces detected',
    );

    const retry = await confirm('Would you like to check for traces again?');
    if (retry) {
      const retried = await pollForTraces(client, state.taskId!);
      if (retried) {
        logSuccess('Instrumentation confirmed. Your traces are flowing to Arthur.');
        note(
          `Login at: ${state.engineUrl}\nTask ID: ${state.taskId}`,
          'Arthur GenAI Engine is ready',
        );
      } else {
        logWarn('Still no traces. Please review the troubleshooting checklist above.');
        note(
          `Arthur Engine URL: ${state.engineUrl}\nTask ID: ${state.taskId}`,
          'Manual verification needed',
        );
      }
    }
  }
}
