import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import * as dotenv from 'dotenv';

export const BUZZ_ENV_PATH = path.join(
  os.homedir(),
  '.arthur-engine',
  'local-stack',
  'buzz',
  '.env',
);

export const GENAI_ENGINE_ENV_PATH = path.join(
  os.homedir(),
  '.arthur-engine',
  'local-stack',
  'genai-engine',
  '.env',
);

export const GENAI_ENGINE_DIR = path.join(
  os.homedir(),
  '.arthur-engine',
  'local-stack',
  'genai-engine',
);

export interface BuzzConfig {
  ARTHUR_ENGINE_URL?: string;
  ARTHUR_API_KEY?: string;
  ARTHUR_TASK_ID?: string;
}

export function readBuzzConfig(envPath = BUZZ_ENV_PATH): BuzzConfig {
  if (!fs.existsSync(envPath)) return {};
  const result = dotenv.config({ path: envPath, override: false, processEnv: {} });
  return (result.parsed ?? {}) as BuzzConfig;
}

export function writeBuzzConfig(config: Partial<BuzzConfig>, envPath = BUZZ_ENV_PATH): void {
  fs.mkdirSync(path.dirname(envPath), { recursive: true });
  const existing = readBuzzConfig(envPath);
  const merged = { ...existing, ...config };
  const content = Object.entries(merged)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${k}=${v}`)
    .join('\n');
  fs.writeFileSync(envPath, content + '\n', 'utf-8');
}

export function readGenaiEngineConfig(): Record<string, string> {
  if (!fs.existsSync(GENAI_ENGINE_ENV_PATH)) return {};
  const result = dotenv.config({ path: GENAI_ENGINE_ENV_PATH, override: false, processEnv: {} });
  return (result.parsed ?? {}) as Record<string, string>;
}
