import { step1_VerifyPrereqs } from './steps/01-prereqs.js';
import { step2_EnsureArthurEngine } from './steps/02-arthur-engine.js';
import { step3_EnsureTaskId } from './steps/03-task.js';
import { step4_InstrumentPython } from './steps/04-python.js';
import { step5_InstrumentMastra } from './steps/05-mastra.js';
import { step6_InstrumentOther } from './steps/06-other.js';
import { step7_VerifyInstrumentation } from './steps/07-verify.js';
import { analyzeRepository, type CodeAnalysisResult } from '../mastra/index.js';
import { p, buzzSay } from '../ui/prompts.js';
import ora from 'ora';

export interface WorkflowState {
  repoPath: string;
  engineUrl: string | null;
  apiKey: string | null;
  taskId: string | null;
  analysis: CodeAnalysisResult | null;
}

function stepBanner(n: number, title: string): void {
  p.log.info(buzzSay(`Step ${n}/7 — ${title}`));
}

export async function runBuzzWorkflow(repoPath: string): Promise<void> {
  const state: WorkflowState = {
    repoPath,
    engineUrl: null,
    apiKey: null,
    taskId: null,
    analysis: null,
  };

  stepBanner(1, 'Verify pre-requisites');
  await step1_VerifyPrereqs(state);

  stepBanner(2, 'Ensure Arthur GenAI Engine is available');
  await step2_EnsureArthurEngine(state);

  stepBanner(3, 'Set up Arthur task ID');
  await step3_EnsureTaskId(state);

  const analysisSpinner = ora({ text: buzzSay('Analyzing repository language and framework...'), color: 'cyan' }).start();
  state.analysis = await analyzeRepository(state.repoPath);
  analysisSpinner.stop();

  stepBanner(4, 'Instrument your agentic application');
  const instrumented =
    (await step4_InstrumentPython(state)) ||
    (await step5_InstrumentMastra(state)) ||
    (await step6_InstrumentOther(state));

  if (!instrumented) {
    p.log.warn(buzzSay('Could not determine application type. Skipping instrumentation.'));
  }

  stepBanner(7, 'Verify instrumentation is working');
  await step7_VerifyInstrumentation(state);
}
