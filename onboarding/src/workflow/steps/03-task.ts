import ora from 'ora';
import { BuzzError } from '../../errors.js';
import {
  p,
  buzzSay,
  logSuccess,
  logError,
  note,
  confirm,
  select,
  text,
} from '../../ui/prompts.js';
import { readBuzzConfig, writeBuzzConfig } from '../../config/env.js';
import { ArthurEngineClient } from '../../arthur/client.js';
import type { WorkflowState } from '../orchestrator.js';

export async function step3_EnsureTaskId(state: WorkflowState): Promise<void> {
  const client = new ArthurEngineClient(state.engineUrl!, state.apiKey!);
  const buzzCfg = readBuzzConfig(state.buzzEnvPath);

  // 1. Check if task ID already persisted
  if (buzzCfg.ARTHUR_TASK_ID) {
    const taskId = buzzCfg.ARTHUR_TASK_ID;
    note(`Existing task ID found:\n  ${taskId}`, 'Saved task ID');

    const confirmed = await confirm(`Is ${taskId} the correct task for this application?`);
    if (confirmed) {
      state.taskId = taskId;
      logSuccess(`Task ID confirmed: ${taskId}`);
      return;
    }
    // User said no — fall through to selection
  }

  // 2. Fetch active tasks from Arthur Engine
  const spinner = ora({ text: buzzSay('Retrieving active tasks from Arthur Engine...'), color: 'cyan' }).start();
  let tasks: Awaited<ReturnType<typeof client.getTasks>> = [];

  try {
    tasks = await client.getTasks();
    spinner.stop();
    logSuccess(`Found ${tasks.length} active task(s).`);
  } catch (err) {
    spinner.stop();
    logError(`Failed to retrieve tasks: ${err instanceof Error ? err.message : String(err)}`);
    throw new BuzzError('Could not retrieve tasks from Arthur Engine.');
  }

  // 3. Build selection options
  if (tasks.length > 0) {
    const options: { value: string; label: string; hint?: string }[] = tasks.map(t => ({
      value: t.id,
      label: t.name,
      hint: t.id,
    }));
    options.push({ value: '__new__', label: '+ Create a new task', hint: 'Give your application a name' });

    const selected = await select('Which Arthur task should we use for this application?', options);

    if (selected !== '__new__') {
      writeBuzzConfig({ ARTHUR_TASK_ID: selected }, state.buzzEnvPath);
      state.taskId = selected;
      logSuccess(`Task selected: ${selected}`);
      return;
    }
  } else {
    p.log.info(buzzSay('No active tasks found. Let\'s create one.'));
  }

  // 4. Create a new task
  const taskName = await text(
    'What should we call this task? (e.g., "My Customer Support Bot"):',
    'My Agentic Application',
  );

  const createSpinner = ora({ text: buzzSay(`Creating task "${taskName}"...`), color: 'cyan' }).start();
  try {
    const newTask = await client.createTask(taskName);
    createSpinner.stop();
    logSuccess(`Task created: "${newTask.name}" (${newTask.id})`);
    writeBuzzConfig({ ARTHUR_TASK_ID: newTask.id }, state.buzzEnvPath);
    state.taskId = newTask.id;
    note(`Task ID: ${newTask.id}\nThis has been saved to ${state.buzzEnvPath}`, 'New task created');
  } catch (err) {
    createSpinner.stop();
    logError(`Failed to create task: ${err instanceof Error ? err.message : String(err)}`);
    throw new BuzzError('Could not create a task in Arthur Engine.');
  }
}
