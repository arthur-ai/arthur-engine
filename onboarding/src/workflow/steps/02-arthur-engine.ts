import fs from 'node:fs';
import path from 'node:path';
import ora from 'ora';
import { execa } from 'execa';
import { BuzzError } from '../../errors.js';
import {
  p,
  buzzSay,
  logSuccess,
  logError,
  logWarn,
  note,
  confirm,
  select,
  text,
  password,
} from '../../ui/prompts.js';
import {
  GENAI_ENGINE_DIR,
  readGenaiEngineConfig,
  readBuzzConfig,
  writeBuzzConfig,
} from '../../config/env.js';
import { ArthurEngineClient } from '../../arthur/client.js';
import type { WorkflowState } from '../orchestrator.js';

const DOCKER_COMPOSE_PATH = path.join(GENAI_ENGINE_DIR, 'docker-compose.yml');
const ENV_PATH = path.join(GENAI_ENGINE_DIR, '.env');
const INSTALL_SCRIPT = 'bash <(curl -sSL https://get-genai-engine.arthur.ai/mac)';

async function waitForEngine(url: string, apiKey: string, maxWaitMs = 120_000): Promise<boolean> {
  const client = new ArthurEngineClient(url, apiKey);
  const start = Date.now();
  const spinner = ora({ text: buzzSay('Waiting for Arthur Engine to become ready...'), color: 'cyan' }).start();

  while (Date.now() - start < maxWaitMs) {
    if (await client.verifyConnection()) {
      spinner.succeed(buzzSay('Arthur Engine is online.'));
      return true;
    }
    await new Promise<void>(r => setTimeout(r, 5_000));
    spinner.text = buzzSay(`Waiting for engine... (${Math.round((Date.now() - start) / 1000)}s)`);
  }

  spinner.fail(buzzSay('Engine did not become ready in time.'));
  return false;
}

async function verifyAndLogin(url: string, apiKey: string): Promise<void> {
  const client = new ArthurEngineClient(url, apiKey);

  const spinner = ora({ text: buzzSay('Verifying Arthur Engine connection...'), color: 'cyan' }).start();
  const reachable = await client.verifyConnection();
  if (!reachable) {
    spinner.fail();
    logError(`Arthur Engine at ${url} is not reachable.`);
    throw new BuzzError(`Engine at ${url} is not reachable.`);
  }
  spinner.text = buzzSay('Engine reachable. Verifying API key...');

  const loggedIn = await client.login();
  if (!loggedIn) {
    spinner.fail();
    logError('API key is invalid. Cannot authenticate with Arthur Engine.');
    throw new BuzzError('Arthur Engine API key is invalid.');
  }

  spinner.succeed(buzzSay('Arthur Engine connection and authentication verified.'));
}

async function handleLocalInstall(state: WorkflowState): Promise<void> {
  note(
    `Running the Arthur GenAI Engine install script:\n  ${INSTALL_SCRIPT}\n\nThis will install Docker and start the local engine.`,
    'Installing Arthur GenAI Engine',
  );

  const proceed = await confirm('Ready to run the local install script?');
  if (!proceed) {
    throw new BuzzError('Installation cancelled by user.');
  }

  p.log.info(buzzSay('Initiating Arthur Engine launch sequence...'));

  try {
    await execa('bash', ['-c', INSTALL_SCRIPT], { stdio: 'inherit' });
  } catch (err) {
    logError('Install script failed.');
    throw new BuzzError(`Install script failed: ${err instanceof Error ? err.message : String(err)}`);
  }

  // Read the newly written .env
  const cfg = readGenaiEngineConfig();
  const url = cfg.GENAI_ENGINE_INGRESS_URI ?? 'http://localhost:3030';
  const apiKey = cfg.GENAI_ENGINE_ADMIN_KEY ?? '';

  if (!apiKey) {
    logWarn('Could not read API key from installed engine config. Using empty key for now.');
  }

  const ready = await waitForEngine(url, apiKey);
  if (!ready) {
    throw new BuzzError('Arthur Engine did not start in time. Check Docker logs.');
  }

  writeBuzzConfig({ ARTHUR_ENGINE_URL: url, ARTHUR_API_KEY: apiKey });
  state.engineUrl = url;
  state.apiKey = apiKey;
  logSuccess(`All systems nominal. Local Arthur Engine ready at ${url}`);
}

async function handleRemoteEngine(state: WorkflowState): Promise<void> {
  note(
    'Enter the URL and API key for your remote Arthur GenAI Engine.\nExample URL: https://myengine.example.com',
    'Remote Arthur Engine',
  );

  const url = await text('Arthur Engine URL:', 'https://myengine.example.com');
  const apiKey = await password('Arthur Engine API key:');

  await verifyAndLogin(url, apiKey);

  writeBuzzConfig({ ARTHUR_ENGINE_URL: url, ARTHUR_API_KEY: apiKey });
  state.engineUrl = url;
  state.apiKey = apiKey;
  logSuccess(`All systems nominal. Remote Arthur Engine configured at ${url}`);
}

export async function step2_EnsureArthurEngine(state: WorkflowState): Promise<void> {
  // Check persisted config first
  const buzzCfg = readBuzzConfig();
  if (buzzCfg.ARTHUR_ENGINE_URL && buzzCfg.ARTHUR_API_KEY) {
    const useExisting = await confirm(
      `Found Arthur Engine config at ${buzzCfg.ARTHUR_ENGINE_URL}. Use this?`,
    );
    if (useExisting) {
      await verifyAndLogin(buzzCfg.ARTHUR_ENGINE_URL, buzzCfg.ARTHUR_API_KEY);
      state.engineUrl = buzzCfg.ARTHUR_ENGINE_URL;
      state.apiKey = buzzCfg.ARTHUR_API_KEY;
      return;
    }
  }

  // Check macOS
  if (process.platform !== 'darwin') {
    logError('This mission currently requires Mac OS hardware. Returning to base.');
    note(
      'Arthur Engine local installation is currently Mac-only.\nFor a remote engine, re-run Buzz and choose the "Remote" option.',
      'Mac only',
    );
    throw new BuzzError('Local Arthur Engine installation requires macOS.', true);
  }

  // Check if local engine already installed
  const localInstalled = fs.existsSync(DOCKER_COMPOSE_PATH) && fs.existsSync(ENV_PATH);

  if (localInstalled) {
    const cfg = readGenaiEngineConfig();
    const localUrl = cfg.GENAI_ENGINE_INGRESS_URI ?? 'http://localhost:3030';

    const useLocal = await confirm(
      `Found a local Arthur Engine installation at ${localUrl}. Use this?`,
    );

    if (useLocal) {
      const apiKey = cfg.GENAI_ENGINE_ADMIN_KEY ?? '';
      await verifyAndLogin(localUrl, apiKey);
      writeBuzzConfig({ ARTHUR_ENGINE_URL: localUrl, ARTHUR_API_KEY: apiKey });
      state.engineUrl = localUrl;
      state.apiKey = apiKey;
      return;
    }
  }

  // Ask: local install or remote
  const choice = await select<'local' | 'remote'>(
    'Where should we connect Arthur GenAI Engine?',
    [
      { value: 'local', label: 'Install on this machine (Mac)', hint: 'Requires Docker' },
      { value: 'remote', label: 'Connect to a remote deployment', hint: 'Need URL + API key' },
    ],
  );

  if (choice === 'local') {
    await handleLocalInstall(state);
  } else {
    await handleRemoteEngine(state);
  }

  // Final login check
  const client = new ArthurEngineClient(state.engineUrl!, state.apiKey!);
  const loggedIn = await client.login();
  if (!loggedIn) {
    throw new BuzzError('Failed to authenticate with Arthur GenAI Engine.');
  }
  logSuccess('Login verified. Arthur Engine is go.');
}
