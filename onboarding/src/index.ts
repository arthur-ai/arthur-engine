#!/usr/bin/env node
import figlet from 'figlet';
import chalk from 'chalk';
import { intro, outro } from '@clack/prompts';
import { runBuzzWorkflow } from './workflow/orchestrator.js';
import { playStartupAnimation, printAvatar } from './ui/avatar.js';
import { buzzSay } from './ui/prompts.js';
import { BuzzError } from './errors.js';

async function main(): Promise<void> {
  // Banner + animated avatar side by side
  const banner = figlet.textSync('BUZZ', { font: 'Big' });
  const bannerLines = banner.split('\n').filter(l => l.length > 0).map(l => chalk.hex('#CE93D8').bold(l));
  await playStartupAnimation(bannerLines);
  console.log(chalk.dim('  Arthur GenAI Engine Onboarding Agent'));
  console.log();

  // Intro
  intro(chalk.cyan.bold(' Arthur GenAI Engine — Onboarding '));

  const repoPath = process.cwd();

  try {
    await runBuzzWorkflow(repoPath);

    console.log();
    printAvatar('success', buzzSay('Mission accomplished. We are go for science!'));
    outro(chalk.green.bold('Your application is now connected to Arthur GenAI Engine.'));
  } catch (err) {
    console.log();

    if (err instanceof BuzzError) {
      printAvatar('error', buzzSay(`Houston, we have a problem. ${err.message}`));
      outro(chalk.red('Mission aborted. Check the messages above for guidance.'));
    } else {
      const msg = err instanceof Error ? err.message : String(err);
      printAvatar('error', buzzSay(`Unexpected error: ${msg}`));
      outro(chalk.red('Mission aborted due to an unexpected error.'));
    }

    process.exit(1);
  }
}

main().catch(err => {
  console.error(chalk.red('\nFatal error:'), err);
  process.exit(1);
});
