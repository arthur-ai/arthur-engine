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

/** Read GENAI_ENGINE_ADMIN_KEY from .env first, then fall back to docker-compose.yml environment block. */
function readLocalAdminKey(): string {
  const cfg = readGenaiEngineConfig();
  if (cfg.GENAI_ENGINE_ADMIN_KEY) return cfg.GENAI_ENGINE_ADMIN_KEY;
  if (!fs.existsSync(DOCKER_COMPOSE_PATH)) return '';
  const content = fs.readFileSync(DOCKER_COMPOSE_PATH, 'utf-8');
  const match = content.match(/^\s*-\s*GENAI_ENGINE_ADMIN_KEY=(.+)$/m);
  return match ? match[1].trim() : '';
}

async function waitForEngine(
  url: string,
  apiKey: string,
  options: { watchDocker?: boolean } = {},
): Promise<boolean> {
  const client = new ArthurEngineClient(url, apiKey);
  const start = Date.now();
  const watchDocker = options.watchDocker === true && fs.existsSync(DOCKER_COMPOSE_PATH);

  if (watchDocker) {
    p.log.info(buzzSay('First-time startup may take several minutes while models are downloaded.'));
    p.log.info(buzzSay('Subsequent startups will load them from the local cache on disk.'));
  }

  const spinner = ora({ text: buzzSay('Waiting for Arthur Engine to become ready...'), color: 'cyan' }).start();

  let recentLogLine = '';
  const logsProcess = watchDocker
    ? execa('docker', ['compose', '-f', DOCKER_COMPOSE_PATH, 'logs', '--follow', '--tail', '10', '--no-color'], {
        all: true,
        reject: false,
      })
    : null;

  logsProcess?.all?.on('data', (chunk: Buffer) => {
    const text = chunk.toString();
    const lines = text.split('\n').filter(l => l.trim() && !l.includes('Attaching to'));
    for (const line of lines) {
      const stripped = line.replace(/^[\w-]+-\d+\s*\|\s*/, '').trim();
      if (stripped) recentLogLine = stripped.slice(0, 120);
    }
  });

  try {
    while (true) {
      if (await client.verifyConnection()) {
        spinner.stop();
        logSuccess('Arthur Engine is online.');
        return true;
      }

      if (watchDocker) {
        // Only give up if the container has stopped — model downloads can take a long time
        try {
          const { stdout } = await execa('docker', [
            'compose', '-f', DOCKER_COMPOSE_PATH, 'ps', '--status', 'running', '-q',
          ]);
          if (!stdout.trim()) {
            spinner.stop();
            logError('Arthur Engine container has exited unexpectedly.');
            return false;
          }
        } catch {
          // Docker check failed — keep waiting
        }
      } else if (Date.now() - start >= 120_000) {
        spinner.stop();
        logError('Engine did not become ready in time.');
        return false;
      }

      await new Promise<void>(r => setTimeout(r, 5_000));
      const elapsed = Math.round((Date.now() - start) / 1000);
      const logHint = recentLogLine ? `\n  ${recentLogLine}` : '';
      spinner.text = buzzSay(`Engine starting up... (${elapsed}s elapsed)${logHint}`);
    }
  } finally {
    logsProcess?.kill();
  }
}

type LocalEngineStatus =
  | { status: 'running'; url: string; apiKey: string }
  | { status: 'down'; url: string; apiKey: string }
  | { status: 'not-installed' };

async function detectLocalArthurEngine(): Promise<LocalEngineStatus> {
  if (!fs.existsSync(DOCKER_COMPOSE_PATH) || !fs.existsSync(ENV_PATH)) {
    return { status: 'not-installed' };
  }

  const cfg = readGenaiEngineConfig();
  const url = cfg.GENAI_ENGINE_INGRESS_URI ?? 'http://localhost:3030';
  const apiKey = readLocalAdminKey();

  try {
    const { stdout } = await execa('docker', ['compose', '-f', DOCKER_COMPOSE_PATH, 'ps', '--status', 'running', '-q']);
    if (!stdout.trim()) return { status: 'down', url, apiKey };
  } catch {
    return { status: 'down', url, apiKey };
  }

  const client = new ArthurEngineClient(url, apiKey);
  if (!(await client.verifyConnection())) return { status: 'down', url, apiKey };

  return { status: 'running', url, apiKey };
}

async function verifyAndLogin(url: string, apiKey: string): Promise<void> {
  const client = new ArthurEngineClient(url, apiKey);

  const spinner = ora({ text: buzzSay('Verifying Arthur Engine connection...'), color: 'cyan' }).start();
  const reachable = await client.verifyConnection();
  if (!reachable) {
    spinner.stop();
    logError(`Arthur Engine at ${url} is not reachable.`);
    throw new BuzzError(`Engine at ${url} is not reachable.`);
  }
  spinner.text = buzzSay('Engine reachable. Verifying API key...');

  const loggedIn = await client.login();
  if (!loggedIn) {
    spinner.stop();
    logError('API key is invalid. Cannot authenticate with Arthur Engine.');
    throw new BuzzError('Arthur Engine API key is invalid.');
  }

  spinner.stop();
  logSuccess('Arthur Engine connection and authentication verified.');
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

  // Read the newly written config
  const cfg = readGenaiEngineConfig();
  const url = cfg.GENAI_ENGINE_INGRESS_URI ?? 'http://localhost:3030';
  let apiKey = readLocalAdminKey();

  if (!apiKey) {
    logWarn('Could not find API key in engine config files.');
    apiKey = await password('Enter your Arthur Engine admin API key:');
  }

  const ready = await waitForEngine(url, apiKey, { watchDocker: true });
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

function isLocalEngine(url: string): boolean {
  return url.includes('localhost') || url.includes('127.0.0.1');
}

export async function step2_EnsureArthurEngine(state: WorkflowState): Promise<void> {
  // Check persisted config first
  const buzzCfg = readBuzzConfig();
  if (buzzCfg.ARTHUR_ENGINE_URL && buzzCfg.ARTHUR_API_KEY) {
    const useExisting = await confirm(
      `Found Arthur Engine config at ${buzzCfg.ARTHUR_ENGINE_URL}. Use this?`,
    );
    if (useExisting) {
      const url = buzzCfg.ARTHUR_ENGINE_URL;
      const apiKey = buzzCfg.ARTHUR_API_KEY;

      const spinner = ora({ text: buzzSay('Verifying Arthur Engine connection...'), color: 'cyan' }).start();
      const reachable = await new ArthurEngineClient(url, apiKey).verifyConnection();
      spinner.stop();

      if (reachable) {
        await verifyAndLogin(url, apiKey);
        state.engineUrl = url;
        state.apiKey = apiKey;
        return;
      }

      logWarn(`Arthur Engine at ${url} is not reachable.`);

      if (isLocalEngine(url)) {
        const recovery = await select<'wait' | 'install'>(
          'What would you like to do?',
          [
            { value: 'wait', label: "I'll bring it back up", hint: 'Buzz will wait until the engine is ready' },
            { value: 'install', label: 'Rerun the Arthur GenAI Engine installer', hint: 'Re-runs the install script' },
          ],
        );
        if (recovery === 'wait') {
          const ready = await waitForEngine(url, apiKey, { watchDocker: true });
          if (!ready) throw new BuzzError('Arthur Engine did not come back online in time. Check Docker logs.');
          await verifyAndLogin(url, apiKey);
          state.engineUrl = url;
          state.apiKey = apiKey;
          logSuccess(`All systems nominal. Arthur Engine back online at ${url}`);
          return;
        } else {
          await handleLocalInstall(state);
          return;
        }
      } else {
        const recovery = await select<'retry' | 'remote'>(
          'What would you like to do?',
          [
            { value: 'retry', label: 'Check again', hint: 'Try reconnecting to the same URL' },
            { value: 'remote', label: 'Connect to a different remote engine', hint: 'Need URL + API key' },
          ],
        );
        if (recovery === 'retry') {
          await verifyAndLogin(url, apiKey);
          state.engineUrl = url;
          state.apiKey = apiKey;
          return;
        } else {
          await handleRemoteEngine(state);
          return;
        }
      }
    }
  }

  // Check for a local Arthur Engine installation
  const local = await detectLocalArthurEngine();
  if (local.status === 'running') {
    const useLocal = await confirm(
      `Detected Arthur Engine running at ${local.url}. Use this?`,
    );
    if (useLocal) {
      await verifyAndLogin(local.url, local.apiKey);
      writeBuzzConfig({ ARTHUR_ENGINE_URL: local.url, ARTHUR_API_KEY: local.apiKey });
      state.engineUrl = local.url;
      state.apiKey = local.apiKey;
      return;
    }
  } else if (local.status === 'down') {
    logWarn(`Found a local Arthur Engine installation at ${local.url} but it is not reachable.`);
    const recovery = await select<'restart' | 'install'>(
      'What would you like to do?',
      [
        { value: 'restart', label: "I'll bring it back up", hint: 'Buzz will wait until the engine is ready' },
        { value: 'install', label: 'Run a fresh install', hint: 'Re-runs the install script' },
      ],
    );
    if (recovery === 'restart') {
      const ready = await waitForEngine(local.url, local.apiKey, { watchDocker: true });
      if (!ready) {
        throw new BuzzError('Arthur Engine did not come back online in time. Check Docker logs.');
      }
      await verifyAndLogin(local.url, local.apiKey);
      writeBuzzConfig({ ARTHUR_ENGINE_URL: local.url, ARTHUR_API_KEY: local.apiKey });
      state.engineUrl = local.url;
      state.apiKey = local.apiKey;
      logSuccess(`All systems nominal. Arthur Engine back online at ${local.url}`);
      return;
    } else {
      await handleLocalInstall(state);
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
