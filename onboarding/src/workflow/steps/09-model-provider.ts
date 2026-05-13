import ora from 'ora';
import {
  buzzSay,
  logSuccess,
  logWarn,
  logError,
  logInfo,
  note,
  confirm,
  select,
  password,
} from '../../ui/prompts.js';
import { ArthurEngineClient } from '../../arthur/client.js';
import type { ModelProviderInfo } from '../../arthur/client.js';
import type { WorkflowState } from '../orchestrator.js';

const PROVIDER_PRIORITY = ['openai', 'anthropic', 'gemini', 'bedrock', 'vertex_ai'];

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini (AI Studio)',
  bedrock: 'AWS Bedrock',
  vertex_ai: 'Google Vertex AI',
};

const MODEL_DEFAULTS: Record<string, string> = {
  openai: 'gpt-4o',
  anthropic: 'claude-3-5-haiku-20241022',
  gemini: 'gemini-1.5-flash',
  bedrock: 'anthropic.claude-3-haiku-20240307-v1:0',
  vertex_ai: 'gemini-1.5-flash',
};

function pickHighestPriorityProvider(
  providers: ModelProviderInfo[],
): { provider: string; model: string } | null {
  const enabled = providers.filter(p => p.enabled);
  for (const name of PROVIDER_PRIORITY) {
    const match = enabled.find(e => e.provider === name);
    if (match && MODEL_DEFAULTS[name]) {
      return { provider: name, model: MODEL_DEFAULTS[name] };
    }
  }
  return null;
}

async function configureNewProvider(
  client: ArthurEngineClient,
): Promise<{ provider: string; model: string } | null> {
  const provider = await select<string>(
    'Which LLM provider should Arthur use to run evaluations?',
    [
      { value: 'openai',    label: 'OpenAI',            hint: 'gpt-4o, gpt-4o-mini, ...' },
      { value: 'anthropic', label: 'Anthropic',         hint: 'claude-3-5-haiku, claude-3-5-sonnet, ...' },
      { value: 'gemini',    label: 'Google Gemini',     hint: 'gemini-1.5-flash, gemini-1.5-pro, ...' },
      { value: 'bedrock',   label: 'AWS Bedrock',       hint: 'anthropic.claude-3-haiku, ...' },
      { value: 'vertex_ai', label: 'Google Vertex AI',  hint: 'gemini-1.5-flash, ...' },
      { value: 'skip',      label: 'Skip for now',      hint: 'Configure manually in Arthur Engine UI — evals will be skipped' },
    ],
  );

  if (provider === 'skip') {
    note(
      'You can configure a model provider in the Arthur Engine UI under Settings → Model Providers.',
      'Eval model provider skipped',
    );
    return null;
  }

  const apiKey = await password(`Enter your ${PROVIDER_LABELS[provider]} API key:`);

  const spinner = ora({ text: buzzSay(`Configuring ${PROVIDER_LABELS[provider]}...`), color: 'cyan' }).start();
  const result = await client.configureModelProvider(provider, { api_key: apiKey });
  spinner.stop();

  if (!result.success) {
    logError(`Failed to configure ${PROVIDER_LABELS[provider]}: ${result.error}`);
    note(
      'You can configure a model provider manually in the Arthur Engine UI under Settings → Model Providers.',
      'Configuration failed',
    );
    return null;
  }

  logSuccess(`${PROVIDER_LABELS[provider]} configured successfully.`);
  return { provider, model: MODEL_DEFAULTS[provider] };
}

export async function step9_SelectEvalModelProvider(state: WorkflowState): Promise<void> {
  const client = new ArthurEngineClient(state.engineUrl!, state.apiKey!);

  const spinner = ora({ text: buzzSay('Checking available model providers for evals...'), color: 'cyan' }).start();
  const providers = await client.getModelProviders();
  spinner.stop();

  const auto = pickHighestPriorityProvider(providers);

  if (auto) {
    const enabledSupported = providers.filter(p => p.enabled && MODEL_DEFAULTS[p.provider]);

    logInfo(`Model providers configured on this Arthur Engine:`);
    for (const mp of enabledSupported) {
      logInfo(`  • ${PROVIDER_LABELS[mp.provider] ?? mp.provider}`);
    }

    if (enabledSupported.length === 1) {
      // Only one option — confirm it
      const useAuto = await confirm(
        `Use ${PROVIDER_LABELS[auto.provider] ?? auto.provider} (${auto.model}) to run evaluations?`,
      );
      if (useAuto) {
        state.evalModelProvider = auto.provider;
        state.evalModelName = auto.model;
        logSuccess(`Eval model set: ${auto.model} via ${PROVIDER_LABELS[auto.provider] ?? auto.provider}`);
        return;
      }
      // Fell through — let them configure a new one
      const result = await configureNewProvider(client);
      if (result) {
        state.evalModelProvider = result.provider;
        state.evalModelName = result.model;
        logSuccess(`Eval model set: ${result.model} via ${PROVIDER_LABELS[result.provider] ?? result.provider}`);
      } else {
        logWarn('No eval model provider selected. Eval recommendations will be skipped.');
      }
      return;
    }

    // Multiple providers — go straight to the picker
    const options = enabledSupported.map(p => ({
      value: p.provider,
      label: PROVIDER_LABELS[p.provider] ?? p.provider,
      hint: MODEL_DEFAULTS[p.provider],
    }));
    options.push({ value: 'new', label: 'Configure a different provider', hint: 'Add API key for a new provider' });

    const chosen = await select<string>('Which provider should run evaluations?', options);

    if (chosen === 'new') {
      const result = await configureNewProvider(client);
      if (result) {
        state.evalModelProvider = result.provider;
        state.evalModelName = result.model;
        logSuccess(`Eval model set: ${result.model} via ${PROVIDER_LABELS[result.provider] ?? result.provider}`);
      } else {
        logWarn('No eval model provider selected. Eval recommendations will be skipped.');
      }
    } else {
      state.evalModelProvider = chosen;
      state.evalModelName = MODEL_DEFAULTS[chosen] ?? null;
      logSuccess(`Eval model set: ${state.evalModelName} via ${PROVIDER_LABELS[chosen] ?? chosen}`);
    }

    return;
  }

  // No providers configured at all
  logWarn('No model providers are configured on this Arthur Engine yet.');
  const wantsSetup = await confirm(
    'Would you like to configure one now so Buzz can recommend evals?',
  );

  if (!wantsSetup) {
    note(
      'Eval recommendations require a model provider.\n' +
        'Configure one in the Arthur Engine UI under Settings → Model Providers, then re-run Buzz.',
      'No eval model provider',
    );
    return;
  }

  const result = await configureNewProvider(client);
  if (result) {
    state.evalModelProvider = result.provider;
    state.evalModelName = result.model;
    logSuccess(`Eval model set: ${result.model} via ${PROVIDER_LABELS[result.provider] ?? result.provider}`);
  } else {
    logWarn('No eval model provider configured. Eval recommendations will be skipped.');
  }
}
