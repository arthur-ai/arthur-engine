import { execa } from 'execa';
import ora from 'ora';
import { BuzzError } from '../../errors.js';
import { p, buzzSay, logSuccess, logError, note } from '../../ui/prompts.js';
import type { WorkflowState } from '../orchestrator.js';

export async function step1_VerifyPrereqs(state: WorkflowState): Promise<void> {
  const spinner = ora({ text: buzzSay('Running pre-flight checklist...'), color: 'cyan' }).start();

  // 1.1 Check we're in a git repo
  try {
    const { stdout } = await execa('git', ['status', '--porcelain'], {
      cwd: state.repoPath,
    });
    if (stdout.trim()) {
      spinner.fail(buzzSay('Pre-flight checklist failed.'));
      logError('Cannot proceed — uncommitted work in progress detected in your repository.');
      note('Please commit or stash your changes and re-run Buzz.', 'git status is dirty');
      throw new BuzzError('Git repository has uncommitted changes.');
    }
  } catch (err) {
    if (err instanceof BuzzError) throw err;
    spinner.fail();
    logError('This directory is not a git repository, or git is not installed.');
    throw new BuzzError('Not a git repository.');
  }

  spinner.text = buzzSay('Git status confirmed. Checking Claude Code...');

  // 1.3 Check Claude Code is installed
  const claudeWhich = await execa('which', ['claude']).catch(() => null);
  if (!claudeWhich) {
    spinner.fail(buzzSay('Claude Code not found.'));
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
    spinner.fail();
    logError('Claude Code binary is not responding.');
    throw new BuzzError('Claude Code binary is not working.');
  }

  spinner.text = buzzSay('Checking Claude Code authentication...');

  // 1.4 Check Claude Code is authenticated (requires ANTHROPIC_API_KEY)
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    // Try asking Claude itself
    const authResult = await execa('claude', ['--print', 'say "auth-ok"'], {
      timeout: 10_000,
      reject: false,
    }).catch(() => null);

    if (!authResult || authResult.exitCode !== 0) {
      spinner.fail(buzzSay('Claude Code is not authenticated.'));
      logError('Claude Code is not authenticated. ANTHROPIC_API_KEY is not set.');
      note(
        'Set your API key:\n  export ANTHROPIC_API_KEY=your-key-here\nor run:\n  claude auth login',
        'Authentication required',
      );
      throw new BuzzError('Claude Code is not authenticated.');
    }
  }

  spinner.succeed(buzzSay('All systems go. Pre-flight checklist complete.'));
  p.log.success(
    `  ${buzzSay(`Running in repo: ${state.repoPath}`)}`,
  );
}
