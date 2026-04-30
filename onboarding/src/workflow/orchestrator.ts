import { step1_VerifyPrereqs } from './steps/01-prereqs.js';
import { step2_EnsureArthurEngine } from './steps/02-arthur-engine.js';
import { step3_EnsureTaskId } from './steps/03-task.js';
import { step4_InstrumentPython } from './steps/04-python.js';
import { step5_InstrumentMastra } from './steps/05-mastra.js';
import { step6_InstrumentOther } from './steps/06-other.js';
import { step7_ExtractAndRegisterPrompts } from './steps/07-prompts.js';
import { step8_VerifyInstrumentation } from './steps/08-verify.js';
import { step9_SelectEvalModelProvider } from './steps/09-model-provider.js';
import { step10_RecommendEvals } from './steps/10-evals.js';
import { analyzeRepository, type CodeAnalysisResult } from '../mastra/index.js';
import { getBuzzEnvPath } from '../config/env.js';
import { p, buzzSay } from '../ui/prompts.js';
import ora from 'ora';

export interface WorkflowState {
  repoPath: string;
  buzzEnvPath: string;
  engineUrl: string | null;
  apiKey: string | null;
  taskId: string | null;
  analysis: CodeAnalysisResult | null;
  promptModelProvider: string | null;
  promptModelName: string | null;
  evalModelProvider: string | null;
  evalModelName: string | null;
}

function stepBanner(n: number, title: string): void {
  p.log.info(buzzSay(`Step ${n}/10 — ${title}`));
}

export async function runBuzzWorkflow(repoPath: string): Promise<void> {
  const state: WorkflowState = {
    repoPath,
    buzzEnvPath: getBuzzEnvPath(repoPath),
    engineUrl: null,
    apiKey: null,
    taskId: null,
    analysis: null,
    promptModelProvider: null,
    promptModelName: null,
    evalModelProvider: null,
    evalModelName: null,
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

  stepBanner(7, 'Extract & register prompts');
  try {
    await step7_ExtractAndRegisterPrompts(state);
  } catch {
    p.log.warn(buzzSay('Prompt extraction encountered an error. Skipping.'));
  }

  stepBanner(8, 'Verify instrumentation is working');
  await step8_VerifyInstrumentation(state);

  stepBanner(9, 'Select model provider for evaluations');
  await step9_SelectEvalModelProvider(state);

  stepBanner(10, 'Recommend & configure evals');
  try {
    await step10_RecommendEvals(state);
  } catch {
    p.log.warn(buzzSay('Eval recommendations encountered an error. Skipping.'));
  }
}
