import { query } from '@anthropic-ai/claude-agent-sdk';
import { execa } from 'execa';
import ora from 'ora';
import { BuzzError } from '../../errors.js';
import { buzzSay, logSuccess, logError, note } from '../../ui/prompts.js';
import type { WorkflowState } from '../orchestrator.js';

export async function step1_VerifyPrereqs(state: WorkflowState): Promise<void> {
  const spinner = ora({ text: buzzSay('Running pre-flight checklist...'), color: 'cyan' }).start();

  // 1.1 Check we're in a git repo
  try {
    const { stdout } = await execa('git', ['status', '--porcelain'], {
      cwd: state.repoPath,
    });
    if (stdout.trim()) {
      spinner.stop();
      logError('Cannot proceed — uncommitted work in progress detected in your repository.');
      note('Please commit or stash your changes and re-run Buzz.', 'git status is dirty');
      throw new BuzzError('Git repository has uncommitted changes.');
    }
  } catch (err) {
    if (err instanceof BuzzError) throw err;
    spinner.stop();
    logError('This directory is not a git repository, or git is not installed.');
    throw new BuzzError('Not a git repository.');
  }

  spinner.text = buzzSay('Git status confirmed. Checking Claude Code...');

  // 1.3 Check Claude Code is installed
  const claudeWhich = await execa('which', ['claude']).catch(() => null);
  if (!claudeWhich) {
    spinner.stop();
    logError('Claude Code is not installed.');
    note(
      'Install Claude Code with:\n  npm install -g @anthropic-ai/claude-code\nThen re-run Buzz.',
      'Missing dependency',
    );
    throw new BuzzError('Claude Code is not installed.');
  }

  // Verify the binary runs
  const claudeVersion = await execa('claude', ['--version']).catch(() => null);
  if (!claudeVersion) {
    spinner.stop();
    logError('Claude Code binary is not responding.');
    throw new BuzzError('Claude Code binary is not working.');
  }

  spinner.text = buzzSay('Checking Claude Code authentication...');

  // 1.4 Check Claude Code is authenticated (supports SSO, OAuth, API key, and other auth methods)
  let accountInfo = await query({ prompt: '' }).accountInfo();

  if (!accountInfo) {
    spinner.stop();
    logError('Claude Code is not authenticated.');
    const { password } = await import('../../ui/prompts.js');
    const apiKey = await password('Enter your ANTHROPIC_API_KEY to continue:');
    process.env.ANTHROPIC_API_KEY = apiKey;
    spinner.start(buzzSay('Verifying API key...'));

    accountInfo = await query({ prompt: '' }).accountInfo();
    if (!accountInfo) {
      spinner.stop();
      logError('The provided ANTHROPIC_API_KEY does not appear to be valid.');
      throw new BuzzError('Claude Code is not authenticated.');
    }
  }

  spinner.stop();
  logSuccess('All systems go. Pre-flight checklist complete.');
  logSuccess(`Running in repo: ${state.repoPath}`);
}
