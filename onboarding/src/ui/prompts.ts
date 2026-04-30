import * as p from '@clack/prompts';
import chalk from 'chalk';
import { stripVTControlCharacters } from 'node:util';

export { p };
export const { isCancel, cancel } = p;

const PHRASE_MAP: Record<string, string> = {
  greeting:      '10-4, do you copy? Buzz here. Ready for takeoff.',
  checking:      'Running diagnostics on {item}...',
  success:       'All systems nominal. {item} confirmed.',
  error:         'Houston, we have a problem. {detail}',
  install:       'Initiating {item} launch sequence...',
  waiting:       'Standing by for your input, astronaut.',
  confirm:       'Do you copy? {question}',
  complete:      'Mission accomplished. We are go for science!',
  notMac:        'This mission currently requires Mac OS hardware. Returning to base.',
  dirty:         'Cannot proceed — uncommitted work in progress detected in your repository.',
  claudeInstall: 'Claude Code is not installed.',
  claudeAuth:    'Claude Code is not authenticated.',
};

export function buzzSay(template: string, vars?: Record<string, string>): string {
  let result = template;
  if (vars) {
    for (const [key, value] of Object.entries(vars)) {
      result = result.replace(`{${key}}`, value);
    }
  }
  return chalk.cyan('[ BUZZ ] ') + result;
}

export function buzzPhrase(key: keyof typeof PHRASE_MAP, vars?: Record<string, string>): string {
  return buzzSay(PHRASE_MAP[key] ?? key, vars);
}

export function handleCancel(value: unknown): void {
  if (isCancel(value)) {
    cancel(buzzSay('Mission aborted by astronaut. Safe travels.'));
    process.exit(0);
  }
}

const CI_MODE = process.env.BUZZ_CI === 'true';

export async function confirm(message: string): Promise<boolean> {
  if (CI_MODE) {
    p.log.info(buzzSay(`[CI] Auto-confirming: ${message}`));
    return true;
  }
  const result = await p.confirm({ message: buzzSay(message) });
  handleCancel(result);
  return result as boolean;
}

export async function select<T extends string>(
  message: string,
  options: { value: T; label: string; hint?: string }[],
): Promise<T> {
  if (CI_MODE) {
    p.log.info(buzzSay(`[CI] Auto-selecting: ${options[0].label}`));
    return options[0].value;
  }
  // Cast options to satisfy @clack/prompts internal Option<T> type
  const result = await p.select({ message: buzzSay(message), options: options as never });
  handleCancel(result);
  return result as T;
}

export async function text(message: string, placeholder?: string): Promise<string> {
  const result = await p.text({
    message: buzzSay(message),
    placeholder,
    validate: v => (v.trim() ? undefined : 'This field is required.'),
  });
  handleCancel(result);
  return (result as string).trim();
}

export async function password(message: string): Promise<string> {
  const result = await p.password({ message: buzzSay(message) });
  handleCancel(result);
  return (result as string).trim();
}

export function logSuccess(msg: string): void {
  p.log.success(buzzSay(msg));
}

export function logError(msg: string): void {
  p.log.error(buzzSay(msg));
}

export function logWarn(msg: string): void {
  p.log.warn(buzzSay(msg));
}

export function logInfo(msg: string): void {
  p.log.info(buzzSay(msg));
}

export function note(message: string, title = ''): void {
  const lines = message.split('\n');
  const titleLen = stripVTControlCharacters(title).length;
  const r = Math.max(
    lines.reduce((n, l) => Math.max(n, stripVTControlCharacters(l).length), 0),
    titleLen,
  ) + 2;

  const bar = chalk.gray('│');
  const contentLines = lines
    .map(l => `${bar}  ${chalk.dim(l)}${' '.repeat(r - stripVTControlCharacters(l).length)}${bar}`)
    .join('\n');

  const topDashes = chalk.gray('─'.repeat(Math.max(r - titleLen - 1, 1)) + '╮');
  const top = `${chalk.green('◇')}  ${chalk.reset(title)} ${topDashes}`;
  const bottom = chalk.gray('├' + '─'.repeat(r + 2) + '╯');

  process.stdout.write(`${chalk.gray('│')}\n${top}\n${contentLines}\n${bottom}\n`);
}
