import { query } from '@anthropic-ai/claude-agent-sdk';
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
import type { OpenAIMessage } from '../../arthur/client.js';
import type { WorkflowState } from '../orchestrator.js';

interface ExtractedPrompt {
  name: string;
  messages: OpenAIMessage[];
  model_name: string | null;
  model_provider: string | null;
}

interface ExtractionResult {
  prompts: ExtractedPrompt[];
  detected_model_name: string | null;
  detected_model_provider: string | null;
}

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
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

function isSupportedProvider(provider: string): boolean {
  return provider in MODEL_DEFAULTS;
}

const EXTRACTION_INSTRUCTIONS = `You are Buzz's prompt extraction module. Your job is to analyze an agentic
application's repository and extract all prompt definitions — system prompts, user prompt templates,
and agent instructions.

Use your tools to thoroughly examine the codebase:
1. Glob to see all files
2. Read manifests and key source files
3. Grep for prompt patterns: system_prompt, SYSTEM_PROMPT, systemPrompt, messages, ChatCompletion, etc.

Look for:
- System prompt strings assigned to variables (any language)
- User prompt templates (strings with {variables} or {{variables}})
- Multi-turn message arrays in OpenAI format ([{"role": "system", ...}, {"role": "user", ...}])
- Prompt files (.txt, .md, .jinja2, .j2) that contain prompt templates
- Agent instruction strings passed to agent/chain initialization

Also detect the LLM model and provider the application uses (e.g. from openai.ChatCompletion calls,
from anthropic.Anthropic(), from model= parameters, from environment variable names like OPENAI_API_KEY).
Report the provider exactly as detected (e.g. "azure" if the app uses Azure OpenAI).

Return ONLY a raw JSON object (no markdown, no explanation):
{
  "prompts": [
    {
      "name": "kebab-case-prompt-name",
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
      ],
      "model_name": "gpt-4o" | null,
      "model_provider": "openai" | "anthropic" | "gemini" | "bedrock" | "vertex_ai" | "azure" | null
    }
  ],
  "detected_model_name": "gpt-4o" | null,
  "detected_model_provider": "openai" | "anthropic" | "gemini" | "bedrock" | "vertex_ai" | "azure" | null
}

Rules:
- Only include prompts with actual substantive content (not empty strings or placeholders)
- For user prompt templates with variables, keep the template as-is (e.g. "Summarize: {text}")
- The "name" must be unique, lowercase, kebab-case, and descriptive (e.g. "customer-support-agent", "summarization-prompt")
- If the same prompt appears multiple times (e.g. in tests), include it only once
- model_name and model_provider at prompt level: use values detected for that specific prompt call if known, else null
- detected_model_name/detected_model_provider: the primary model the app uses overall
- If no prompts are found, return {"prompts": [], "detected_model_name": null, "detected_model_provider": null}`;

function extractJSON(text: string): string {
  const blockMatch = text.match(/```(?:json)?\s*([\s\S]+?)```/);
  if (blockMatch) return blockMatch[1].trim();
  const jsonMatch = text.match(/\{[\s\S]+\}/);
  if (jsonMatch) return jsonMatch[0];
  return text.trim();
}

async function extractPromptsWithClaude(repoPath: string): Promise<ExtractionResult> {
  try {
    const stream = query({
      prompt: `Extract all prompts from the agentic application at: ${repoPath}\n\nUse your tools to examine the files thoroughly, then return the JSON result.`,
      options: {
        cwd: repoPath,
        allowedTools: ['Read', 'Glob', 'Grep'],
        systemPrompt: EXTRACTION_INSTRUCTIONS,
        maxTurns: 5,
      },
    });

    let fullOutput = '';
    for await (const message of stream) {
      if (message.type === 'assistant') {
        const content = (message as { type: 'assistant'; message: { content: Array<{ type: string; text?: string }> } }).message?.content ?? [];
        for (const block of content) {
          if (block.type === 'text' && block.text) {
            fullOutput += block.text;
          }
        }
      }
    }

    return JSON.parse(extractJSON(fullOutput)) as ExtractionResult;
  } catch {
    return { prompts: [], detected_model_name: null, detected_model_provider: null };
  }
}

async function ensureProviderConfiguredInEngine(
  client: ArthurEngineClient,
  provider: string,
  model: string | null,
): Promise<void> {
  const spinner = ora({ text: buzzSay(`Checking if ${PROVIDER_LABELS[provider] ?? provider} is configured in Arthur Engine...`), color: 'cyan' }).start();
  const providers = await client.getModelProviders();
  spinner.stop();

  const isConfigured = providers.some(p => p.provider === provider && p.enabled);

  if (isConfigured) {
    logSuccess(`${PROVIDER_LABELS[provider] ?? provider} is already configured in Arthur Engine.`);
    note(
      `Prompts will be registered with model: ${model ?? 'default'} (${PROVIDER_LABELS[provider] ?? provider})`,
      'Prompt model provider',
    );
    return;
  }

  logWarn(`${PROVIDER_LABELS[provider] ?? provider} is not yet configured in Arthur Engine.`);
  note(
    'Arthur Engine needs the API key for this provider to be able to run the prompts.\n' +
      'You can skip this and configure it later in the Arthur Engine UI under Settings → Model Providers.',
    'Model provider required',
  );

  const wantsConfigure = await confirm(
    `Configure ${PROVIDER_LABELS[provider] ?? provider} in Arthur Engine now?`,
  );

  if (!wantsConfigure) {
    logWarn('Skipping provider configuration. Prompts will be registered but cannot be run until a provider is configured.');
    return;
  }

  const apiKey = await password(`Enter your ${PROVIDER_LABELS[provider] ?? provider} API key:`);

  const configSpinner = ora({ text: buzzSay(`Configuring ${PROVIDER_LABELS[provider] ?? provider}...`), color: 'cyan' }).start();
  const result = await client.configureModelProvider(provider, { api_key: apiKey });
  configSpinner.stop();

  if (!result.success) {
    logError(`Failed to configure ${PROVIDER_LABELS[provider] ?? provider}: ${result.error}`);
    logWarn('Prompts will still be registered. Configure the provider manually in Arthur Engine UI.');
  } else {
    logSuccess(`${PROVIDER_LABELS[provider] ?? provider} configured in Arthur Engine.`);
    note(
      `Prompts will be registered with model: ${model ?? 'default'} (${PROVIDER_LABELS[provider] ?? provider})`,
      'Prompt model provider ready',
    );
  }
}

export async function step7_ExtractAndRegisterPrompts(state: WorkflowState): Promise<void> {
  // Extract prompts from the repo
  const spinner = ora({ text: buzzSay('Scanning codebase for prompts...'), color: 'cyan' }).start();
  const extraction = await extractPromptsWithClaude(state.repoPath);
  spinner.stop();

  // Store detected model info on state for use in step 09 as a hint
  if (extraction.detected_model_provider && isSupportedProvider(extraction.detected_model_provider)) {
    state.promptModelProvider = extraction.detected_model_provider;
    state.promptModelName = extraction.detected_model_name ?? MODEL_DEFAULTS[extraction.detected_model_provider] ?? null;
  }

  if (extraction.prompts.length === 0) {
    p.log.info(buzzSay('No prompts detected in the repository. Skipping prompt registration.'));
    return;
  }

  logInfo(`Found ${extraction.prompts.length} prompt(s) in your codebase:`);
  for (const [i, prompt] of extraction.prompts.entries()) {
    const rolesSummary = prompt.messages.map(m => m.role).join(' → ');
    p.log.message(`  ${i + 1}. ${prompt.name}  (${rolesSummary})`);
  }

  const shouldRegister = await confirm(
    `Should Buzz register these ${extraction.prompts.length} prompt(s) in Arthur Engine for version tracking?`,
  );
  if (!shouldRegister) {
    logInfo('Prompt registration skipped. You can add prompts manually in the Arthur Engine UI.');
    return;
  }

  // Resolve model info for prompt creation
  // Each prompt uses its own detected model, falling back to the app-level detected model,
  // then asking the user.
  const detectedRaw = extraction.detected_model_provider;
  let fallbackProvider: string | null = null;
  let fallbackModel = extraction.detected_model_name;

  if (detectedRaw && isSupportedProvider(detectedRaw)) {
    fallbackProvider = detectedRaw;
  } else if (detectedRaw) {
    // Detected a provider that Arthur Engine doesn't support yet
    logWarn(`Your app uses ${detectedRaw}, which isn't currently supported by Arthur Engine.`);
    note(
      'Arthur Engine supports: OpenAI, Anthropic, Google Gemini, AWS Bedrock, Google Vertex AI.\n' +
        'To register prompts you\'ll need to configure one of these providers.',
      'Unsupported provider detected',
    );
  }

  if (!fallbackProvider) {
    // Either couldn't detect or detected an unsupported provider — ask the user
    const choice = await select<string>(
      'Which supported provider should Arthur Engine use to run your prompts?',
      [
        { value: 'openai',    label: 'OpenAI',            hint: 'gpt-4o, gpt-4o-mini, ...' },
        { value: 'anthropic', label: 'Anthropic',         hint: 'claude-3-5-haiku, claude-3-5-sonnet, ...' },
        { value: 'gemini',    label: 'Google Gemini',     hint: 'gemini-1.5-flash, gemini-1.5-pro, ...' },
        { value: 'bedrock',   label: 'AWS Bedrock',       hint: 'anthropic.claude-3-haiku, ...' },
        { value: 'vertex_ai', label: 'Google Vertex AI',  hint: 'gemini-1.5-flash, ...' },
        { value: 'skip',      label: 'Skip — I\'ll set it later', hint: 'Prompts will use a placeholder model' },
      ],
    );

    if (choice !== 'skip') {
      fallbackProvider = choice;
      fallbackModel = MODEL_DEFAULTS[choice] ?? null;
      state.promptModelProvider = fallbackProvider;
      state.promptModelName = fallbackModel;
    }
  }

  // Ensure the chosen provider is actually configured in Arthur Engine
  const client = new ArthurEngineClient(state.engineUrl!, state.apiKey!);

  if (fallbackProvider) {
    await ensureProviderConfiguredInEngine(client, fallbackProvider, fallbackModel);
  } else {
    note(
      'Registering prompts without a model provider configured in Arthur Engine.\n' +
        'You can configure one under Settings → Model Providers and update the prompts there.',
      'No model provider configured',
    );
  }
  let created = 0;

  for (const prompt of extraction.prompts) {
    const rawProvider = prompt.model_provider ?? fallbackProvider ?? 'openai';
    const provider = isSupportedProvider(rawProvider) ? rawProvider : (fallbackProvider ?? 'openai');
    const model = prompt.model_name ?? fallbackModel ?? MODEL_DEFAULTS[provider] ?? 'gpt-4o';

    const promptSpinner = ora({
      text: buzzSay(`Registering prompt: ${prompt.name}...`),
      color: 'cyan',
    }).start();

    const result = await client.createPrompt(state.taskId!, prompt.name, {
      messages: prompt.messages,
      model_name: model,
      model_provider: provider,
    });

    promptSpinner.stop();

    if (result.error) {
      logError(`Failed to register "${prompt.name}": ${result.error}`);
    } else {
      logSuccess(`Registered prompt: ${prompt.name} (v${result.prompt?.version ?? 1})`);
      created++;
    }
  }

  if (created > 0) {
    logSuccess(`${created} prompt(s) registered in Arthur Engine.`);
    note(
      `View and manage your prompts in Arthur Engine:\n  ${state.engineUrl}`,
      'Prompts registered',
    );
  } else {
    logWarn('No prompts were registered. You can add them manually in the Arthur Engine UI.');
  }
}
