import ora from 'ora';
import {
  p,
  buzzSay,
  logSuccess,
  logWarn,
  logInfo,
  logError,
  note,
  confirm,
  select,
  password,
} from '../../ui/prompts.js';
import { ArthurEngineClient } from '../../arthur/client.js';
import type { SpanDetail, TraceDetail, ModelProviderInfo } from '../../arthur/client.js';
import { recommendEvals } from '../../mastra/eval-recommender.js';
import type { RecommendEvalsResult } from '../../mastra/eval-recommender.js';
import type { WorkflowState } from '../orchestrator.js';

const MODEL_DEFAULTS: Record<string, string> = {
  openai: 'gpt-4o',
  anthropic: 'claude-3-5-haiku-20241022',
  gemini: 'gemini-1.5-flash',
  bedrock: 'anthropic.claude-3-haiku-20240307-v1:0',
  vertex_ai: 'gemini-1.5-flash',
};

const PROVIDER_PRIORITY = ['openai', 'anthropic', 'gemini', 'bedrock', 'vertex_ai'];

function pickModel(providers: ModelProviderInfo[]): { provider: string; model: string } | null {
  const enabled = providers.filter(p => p.enabled);
  for (const providerName of PROVIDER_PRIORITY) {
    const match = enabled.find(e => e.provider === providerName);
    if (match && MODEL_DEFAULTS[providerName]) {
      return { provider: providerName, model: MODEL_DEFAULTS[providerName] };
    }
  }
  return null;
}

const RETRIEVAL_SPAN_PATTERN = /retriev|search|fetch|document|rag/i;

function isRetrievalSpan(span: SpanDetail): boolean {
  return (
    span.span_kind === 'RETRIEVER' ||
    (span.span_name != null && RETRIEVAL_SPAN_PATTERN.test(span.span_name))
  );
}

function flattenSpans(spans: SpanDetail[]): SpanDetail[] {
  const result: SpanDetail[] = [];
  for (const span of spans) {
    result.push(span);
    if (span.children?.length) {
      result.push(...flattenSpans(span.children));
    }
  }
  return result;
}

function extractBestSpan(trace: TraceDetail): SpanDetail | null {
  const all = flattenSpans(trace.root_spans ?? []);
  return all.find(s => s.input_content || s.output_content) ?? null;
}

function buildTraceContent(
  span: SpanDetail,
  trace: TraceDetail,
): { content: string; hasRetrievalContext: boolean } {
  const input = span.input_content ? span.input_content.slice(0, 1500) : '(none)';
  const output = span.output_content ? span.output_content.slice(0, 1500) : '(none)';

  const allSpans = flattenSpans(trace.root_spans ?? []);
  const retrievalSpans = allSpans.filter(isRetrievalSpan);
  const hasRetrievalContext = retrievalSpans.length > 0;

  let content = `INPUT:\n${input}\n\nOUTPUT:\n${output}`;

  if (hasRetrievalContext) {
    const contextParts = retrievalSpans
      .map(s => {
        const parts: string[] = [];
        if (s.input_content) parts.push(`Query: ${s.input_content.slice(0, 500)}`);
        if (s.output_content) parts.push(`Retrieved: ${s.output_content.slice(0, 1000)}`);
        return parts.join('\n');
      })
      .filter(Boolean);
    if (contextParts.length > 0) {
      content += `\n\nRETRIEVAL CONTEXT:\n${contextParts.join('\n---\n')}`;
    }
  }

  return { content, hasRetrievalContext };
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini (AI Studio)',
};

async function setupModelProvider(
  client: ArthurEngineClient,
): Promise<{ provider: string; model: string } | null> {
  const wantsSetup = await confirm(
    'No model provider is configured. Would you like Buzz to set one up now?',
  );
  if (!wantsSetup) {
    note(
      'You can configure a model provider in the Arthur Engine UI under Settings → Model Providers,\n' +
        'then re-run Buzz to get personalized eval recommendations.',
      'Model provider setup skipped',
    );
    return null;
  }

  const provider = await select<string>(
    'Which LLM provider would you like to configure?',
    [
      { value: 'openai',    label: 'OpenAI',        hint: 'gpt-4o, gpt-4o-mini, ...' },
      { value: 'anthropic', label: 'Anthropic',     hint: 'claude-3-5-haiku, claude-3-5-sonnet, ...' },
      { value: 'gemini',    label: 'Google Gemini', hint: 'gemini-1.5-flash, gemini-1.5-pro, ...' },
      { value: 'skip',      label: 'Skip for now',  hint: 'Configure manually in the Arthur Engine UI' },
    ],
  );

  if (provider === 'skip') {
    note(
      'You can configure a model provider in the Arthur Engine UI under Settings → Model Providers.',
      'Model provider setup skipped',
    );
    return null;
  }

  const apiKey = await password(`Enter your ${PROVIDER_LABELS[provider]} API key`);

  const spinner = ora({ text: buzzSay('Configuring model provider...'), color: 'cyan' }).start();
  const result = await client.configureModelProvider(provider, { api_key: apiKey });
  spinner.stop();

  if (!result.success) {
    logError(`Failed to configure ${PROVIDER_LABELS[provider]}: ${result.error}`);
    note(
      'You can configure a model provider manually in the Arthur Engine UI under Settings → Model Providers.',
      'Model provider setup failed',
    );
    return null;
  }

  logSuccess(`${PROVIDER_LABELS[provider]} configured successfully.`);
  return { provider, model: MODEL_DEFAULTS[provider] };
}


export async function step8_RecommendEvals(state: WorkflowState): Promise<void> {
  if (!state.engineUrl || !state.apiKey || !state.taskId) {
    logWarn('Skipping eval recommendations — engine connection not established.');
    return;
  }

  const client = new ArthurEngineClient(state.engineUrl, state.apiKey);

  // Phase 1: Discover which model provider is available for running evals
  const providersSpinner = ora({
    text: buzzSay('Checking available model providers...'),
    color: 'cyan',
  }).start();
  const providers = await client.getModelProviders();
  providersSpinner.stop();

  let modelSelection = pickModel(providers);
  if (!modelSelection) {
    modelSelection = await setupModelProvider(client);
    if (!modelSelection) return;
  }

  // Phase 2: Fetch a recent trace for analysis
  const traceSpinner = ora({
    text: buzzSay('Fetching trace data for deep scan...'),
    color: 'cyan',
  }).start();
  const traceResult = await client.getTraces(state.taskId);

  if (traceResult.traces.length === 0) {
    traceSpinner.stop();
    note(
      'Once your application has sent traces to Arthur, re-run Buzz\n' +
        'to get personalized eval recommendations based on your real trace data.',
      'No traces available for analysis',
    );
    return;
  }

  const traceDetail = await client.getTraceDetail(traceResult.traces[0].trace_id);
  traceSpinner.stop();

  if (!traceDetail) {
    logWarn('Could not fetch trace details. Skipping eval recommendations.');
    return;
  }

  const bestSpan = extractBestSpan(traceDetail);
  if (!bestSpan) {
    logWarn('No span content found in trace. Skipping eval recommendations.');
    return;
  }

  // Phase 3: Analyze trace with Claude to generate eval recommendations
  const analysisSpinner = ora({
    text: buzzSay('Deep scanning your application traces with Claude...'),
    color: 'cyan',
  }).start();

  const { content: traceContent, hasRetrievalContext } = buildTraceContent(bestSpan, traceDetail);

  const result: RecommendEvalsResult = await recommendEvals(
    traceContent,
    bestSpan.span_name ?? 'unknown',
    state.analysis?.framework ?? null,
    state.analysis?.language ?? 'unknown',
    modelSelection.provider,
    hasRetrievalContext,
  );
  analysisSpinner.stop();

  if (!result.ok) {
    logWarn(`Could not generate eval recommendations: ${result.reason}`);
    return;
  }

  const recommendations = result.recommendations;

  // Phase 4: Present recommendations and ask for confirmation
  logInfo('Based on your trace data, Buzz recommends these continuous evals:');
  for (const [i, rec] of recommendations.recommendations.entries()) {
    p.log.message(`${i + 1}. ${rec.displayName}`);
    p.log.message(`   ${rec.rationale}`);
  }

  const approved = await confirm(
    'Should Buzz configure these continuous evals on your task now?',
  );
  if (!approved) {
    logInfo(
      'Eval configuration skipped. You can configure evals manually in the Arthur Engine UI.',
    );
    return;
  }

  // Phase 5: Create LLM evals
  const createdEvalSlugs: string[] = [];
  for (const rec of recommendations.recommendations) {
    const spinner = ora({
      text: buzzSay(`Creating LLM eval: ${rec.displayName}...`),
      color: 'cyan',
    }).start();
    const result = await client.createLlmEval(state.taskId, rec.slug, {
      model_name: modelSelection.model,
      model_provider: modelSelection.provider,
      instructions: rec.instructions,
    });
    spinner.stop();
    if (result.error) {
      logError(`Failed to create eval "${rec.displayName}": ${result.error}`);
    } else {
      logSuccess(`Created LLM eval: ${rec.displayName}`);
      createdEvalSlugs.push(rec.slug);
    }
  }

  if (createdEvalSlugs.length === 0) {
    logWarn('No LLM evals were created. Skipping transform and continuous eval setup.');
    return;
  }

  // Phase 6: Create one shared transform
  const transformSpinner = ora({
    text: buzzSay('Creating trace transform...'),
    color: 'cyan',
  }).start();
  const transformResult = await client.createTransform(state.taskId, {
    name: 'Buzz — Input/Output Extractor',
    definition: {
      variables: [
        {
          variable_name: 'input',
          span_name: bestSpan.span_name ?? '',
          attribute_path: 'attributes.input.value',
          fallback: '',
        },
        {
          variable_name: 'output',
          span_name: bestSpan.span_name ?? '',
          attribute_path: 'attributes.output.value',
          fallback: '',
        },
      ],
    },
  });
  transformSpinner.stop();

  if (transformResult.error || !transformResult.transform) {
    logError(`Failed to create transform: ${transformResult.error ?? 'unknown error'}`);
    logWarn('Continuous evals could not be linked without a transform. Configure them manually in the Arthur Engine UI.');
    return;
  }
  logSuccess('Created trace transform');

  // Phase 7: Create continuous evals (one per successfully created LLM eval)
  const VARIABLE_MAPPING = [
    { transform_variable: 'input', eval_variable: 'input' },
    { transform_variable: 'output', eval_variable: 'output' },
  ];

  let continuousEvalCount = 0;
  for (const slug of createdEvalSlugs) {
    const rec = recommendations.recommendations.find(r => r.slug === slug)!;
    const spinner = ora({
      text: buzzSay(`Activating continuous eval: ${rec.displayName}...`),
      color: 'cyan',
    }).start();
    const result = await client.createContinuousEval(state.taskId, {
      name: rec.displayName,
      llm_eval_name: slug,
      llm_eval_version: 'latest',
      transform_id: transformResult.transform.id,
      transform_variable_mapping: VARIABLE_MAPPING,
      enabled: true,
    });
    spinner.stop();
    if (result.error) {
      logError(`Failed to activate "${rec.displayName}": ${result.error}`);
    } else {
      logSuccess(`Activated: ${rec.displayName}`);
      continuousEvalCount++;
    }
  }

  if (continuousEvalCount > 0) {
    logSuccess(
      `${continuousEvalCount} continuous eval(s) are now monitoring your application.`,
    );
    note(
      `View and manage your evals in Arthur Engine:\n  ${state.engineUrl}`,
      'Continuous evals configured',
    );
  } else {
    logWarn('No continuous evals were activated. Configure them manually in the Arthur Engine UI.');
  }
}
