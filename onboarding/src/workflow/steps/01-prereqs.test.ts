import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BuzzError } from '../../errors.js';

vi.mock('execa', () => ({ execa: vi.fn() }));
vi.mock('ora', () => ({
  default: vi.fn(() => {
    const spinner = { start: vi.fn(), stop: vi.fn(), text: '' };
    spinner.start = vi.fn(() => spinner);
    return spinner;
  }),
}));
vi.mock('../../ui/prompts.js', () => ({
  buzzSay: vi.fn((msg: string) => msg),
  logSuccess: vi.fn(),
  logError: vi.fn(),
  note: vi.fn(),
  password: vi.fn(),
}));

import { execa } from 'execa';
import * as prompts from '../../ui/prompts.js';
import { step1_VerifyPrereqs } from './01-prereqs.js';

const mockExeca = vi.mocked(execa);
const mockPassword = vi.mocked(prompts.password as (msg: string) => Promise<string>);

const REPO = '/fake/repo';

function makeResult(exitCode: number, stdout = '') {
  return { exitCode, stdout };
}

function setupBaseCommands(authExitCode: number) {
  // Tracks how many times 'claude auth status' has been called
  let authCalls = 0;
  mockExeca.mockImplementation((cmd: string, args: string[]) => {
    if (cmd === 'git') return Promise.resolve(makeResult(0, '')) as never;
    if (cmd === 'which') return Promise.resolve(makeResult(0, '/usr/bin/claude')) as never;
    if (cmd === 'claude' && args[0] === '--version') return Promise.resolve(makeResult(0, 'claude 1.0')) as never;
    if (cmd === 'claude' && args[0] === 'auth') {
      authCalls++;
      return Promise.resolve(makeResult(authCalls === 1 ? authExitCode : 0)) as never;
    }
    return Promise.reject(new Error(`Unexpected: ${cmd} ${args.join(' ')}`)) as never;
  });
}

describe('step1_VerifyPrereqs — auth check', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.ANTHROPIC_API_KEY;
  });

  it('succeeds without prompting when already authenticated', async () => {
    setupBaseCommands(0);
    await expect(step1_VerifyPrereqs({ repoPath: REPO })).resolves.toBeUndefined();
    expect(mockPassword).not.toHaveBeenCalled();
  });

  it('prompts for API key when not authenticated and accepts a valid key', async () => {
    setupBaseCommands(1);
    mockPassword.mockResolvedValue('sk-ant-valid-key');

    await expect(step1_VerifyPrereqs({ repoPath: REPO })).resolves.toBeUndefined();
    expect(mockPassword).toHaveBeenCalledOnce();
    expect(process.env.ANTHROPIC_API_KEY).toBe('sk-ant-valid-key');
  });

  it('throws BuzzError when the provided API key is also invalid', async () => {
    // Both auth status calls fail
    mockExeca.mockImplementation((cmd: string, args: string[]) => {
      if (cmd === 'git') return Promise.resolve(makeResult(0, '')) as never;
      if (cmd === 'which') return Promise.resolve(makeResult(0, '/usr/bin/claude')) as never;
      if (cmd === 'claude' && args[0] === '--version') return Promise.resolve(makeResult(0)) as never;
      if (cmd === 'claude' && args[0] === 'auth') return Promise.resolve(makeResult(1)) as never;
      return Promise.reject(new Error(`Unexpected: ${cmd}`)) as never;
    });
    mockPassword.mockResolvedValue('bad-key');

    await expect(step1_VerifyPrereqs({ repoPath: REPO })).rejects.toBeInstanceOf(BuzzError);
    await expect(step1_VerifyPrereqs({ repoPath: REPO })).rejects.toThrow('Claude Code is not authenticated.');
  });

  it('treats a failing auth status command (execa rejects) as unauthenticated', async () => {
    let authCalls = 0;
    mockExeca.mockImplementation((cmd: string, args: string[]) => {
      if (cmd === 'git') return Promise.resolve(makeResult(0, '')) as never;
      if (cmd === 'which') return Promise.resolve(makeResult(0, '/usr/bin/claude')) as never;
      if (cmd === 'claude' && args[0] === '--version') return Promise.resolve(makeResult(0)) as never;
      if (cmd === 'claude' && args[0] === 'auth') {
        authCalls++;
        // First call rejects (simulates a crash); second resolves with exitCode 0
        if (authCalls === 1) return Promise.reject(new Error('auth binary crashed')) as never;
        return Promise.resolve(makeResult(0)) as never;
      }
      return Promise.reject(new Error(`Unexpected: ${cmd}`)) as never;
    });
    mockPassword.mockResolvedValue('sk-ant-fallback-key');

    await expect(step1_VerifyPrereqs({ repoPath: REPO })).resolves.toBeUndefined();
    expect(mockPassword).toHaveBeenCalledOnce();
  });
});
