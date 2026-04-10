import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { readBuzzConfig, writeBuzzConfig } from './env.js';

// Use an isolated temp directory so tests don't touch the real ~/.arthur-engine
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'buzz-env-test-'));
const tmpEnvPath = path.join(tmpDir, 'buzz-test.env');

describe('readBuzzConfig', () => {
  beforeEach(() => {
    if (fs.existsSync(tmpEnvPath)) fs.unlinkSync(tmpEnvPath);
  });

  it('returns empty object when file does not exist', () => {
    expect(readBuzzConfig(tmpEnvPath)).toEqual({});
  });

  it('parses existing env file', () => {
    fs.writeFileSync(tmpEnvPath, 'ARTHUR_ENGINE_URL=http://localhost:3030\nARTHUR_API_KEY=abc123\n');
    const cfg = readBuzzConfig(tmpEnvPath);
    expect(cfg.ARTHUR_ENGINE_URL).toBe('http://localhost:3030');
    expect(cfg.ARTHUR_API_KEY).toBe('abc123');
  });
});

describe('writeBuzzConfig', () => {
  beforeEach(() => {
    if (fs.existsSync(tmpEnvPath)) fs.unlinkSync(tmpEnvPath);
  });

  afterEach(() => {
    if (fs.existsSync(tmpEnvPath)) fs.unlinkSync(tmpEnvPath);
  });

  it('creates the file with correct content', () => {
    writeBuzzConfig({ ARTHUR_ENGINE_URL: 'http://localhost:3030', ARTHUR_API_KEY: 'key123' }, tmpEnvPath);
    expect(fs.existsSync(tmpEnvPath)).toBe(true);
    const content = fs.readFileSync(tmpEnvPath, 'utf-8');
    expect(content).toContain('ARTHUR_ENGINE_URL=http://localhost:3030');
    expect(content).toContain('ARTHUR_API_KEY=key123');
  });

  it('merges partial updates without overwriting other keys', () => {
    writeBuzzConfig({ ARTHUR_ENGINE_URL: 'http://localhost:3030', ARTHUR_API_KEY: 'key123' }, tmpEnvPath);
    writeBuzzConfig({ ARTHUR_TASK_ID: 'task-abc' }, tmpEnvPath);
    const cfg = readBuzzConfig(tmpEnvPath);
    expect(cfg.ARTHUR_ENGINE_URL).toBe('http://localhost:3030');
    expect(cfg.ARTHUR_API_KEY).toBe('key123');
    expect(cfg.ARTHUR_TASK_ID).toBe('task-abc');
  });

  it('overwrites existing key with new value', () => {
    writeBuzzConfig({ ARTHUR_TASK_ID: 'old-task' }, tmpEnvPath);
    writeBuzzConfig({ ARTHUR_TASK_ID: 'new-task' }, tmpEnvPath);
    const cfg = readBuzzConfig(tmpEnvPath);
    expect(cfg.ARTHUR_TASK_ID).toBe('new-task');
  });

  it('creates parent directories if they do not exist', () => {
    const nestedPath = path.join(tmpDir, 'a', 'b', 'c', 'test.env');
    writeBuzzConfig({ ARTHUR_ENGINE_URL: 'http://test' }, nestedPath);
    expect(fs.existsSync(nestedPath)).toBe(true);
    // cleanup
    fs.rmSync(path.join(tmpDir, 'a'), { recursive: true, force: true });
  });

  it('writes file ending with newline', () => {
    writeBuzzConfig({ ARTHUR_API_KEY: 'k' }, tmpEnvPath);
    const content = fs.readFileSync(tmpEnvPath, 'utf-8');
    expect(content.endsWith('\n')).toBe(true);
  });
});
