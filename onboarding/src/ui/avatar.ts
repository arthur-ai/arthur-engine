import chalk from 'chalk';
import boxen from 'boxen';

export type AvatarState = 'idle' | 'thinking' | 'success' | 'error';

// ASCII helmet frames
const HELMET_IDLE_A = [
  '  .-""-.  ',
  ' / .-. \\ ',
  '|(  o  )|',
  " \\ '-' / ",
  "  '---'  ",
  '  || ||  ',
  '  \\_|_/  ',
];

const HELMET_IDLE_B = [
  '  .-""-.  ',
  ' / .-. \\ ',
  '|(  O  )|',
  " \\ '-' / ",
  "  '---'  ",
  '  || ||  ',
  '  \\_|_/  ',
];

const HELMET_THINK_FRAMES = [
  [
    '  .-""-.  ',
    ' / .-. \\ ',
    '|(  o  )|',
    " \\ '-' / ",
    "  '-|-'  ",
    '   | |   ',
    '  \\_|_/  ',
  ],
  [
    '  .-""-.  ',
    ' / .\\. \\ ',
    '|(  o  )|',
    " \\ '-' / ",
    "  '-|-'  ",
    '   | |   ',
    '  \\_|_/  ',
  ],
  [
    '  .-""-.  ',
    ' / .-. \\ ',
    '|(  o  )|',
    " \\ '-' / ",
    "  '-|-'  ",
    '   | |   ',
    '  \\_|_/  ',
  ],
  [
    '  .-""-.  ',
    ' / /.-. \\ ',
    '|(  o  )|',
    " \\ '-' / ",
    "  '-|-'  ",
    '   | |   ',
    '  \\_|_/  ',
  ],
];

const HELMET_SUCCESS = [
  '    *    ',
  '   \\|/   ',
  '  .-O-.  ',
  '   /|\\   ',
  '    *    ',
  '  || ||  ',
  '  \\_|_/  ',
];

const HELMET_ERROR = [
  '  .-""-.  ',
  ' / .-. \\ ',
  '|(  X  )|',
  " \\ '-' / ",
  "  '---'  ",
  '  || ||  ',
  '  \\_|_/  ',
];

function renderFrame(lines: string[], colorFn: (s: string) => string): string {
  return lines.map(l => colorFn(l)).join('\n');
}

export function printAvatar(state: AvatarState, message: string): void {
  let frame: string[];
  let colorFn: (s: string) => string;

  switch (state) {
    case 'success':
      frame = HELMET_SUCCESS;
      colorFn = chalk.green;
      break;
    case 'error':
      frame = HELMET_ERROR;
      colorFn = chalk.red;
      break;
    case 'thinking':
      frame = HELMET_THINK_FRAMES[0];
      colorFn = chalk.yellow;
      break;
    default:
      frame = HELMET_IDLE_A;
      colorFn = chalk.cyan;
  }

  console.log(renderFrame(frame, colorFn));
  console.log(
    boxen(message, {
      padding: { top: 0, bottom: 0, left: 1, right: 1 },
      borderStyle: 'round',
      borderColor: 'cyan',
      width: 60,
    }),
  );
  console.log();
}

export async function playStartupAnimation(): Promise<void> {
  const frames = [HELMET_IDLE_A, HELMET_IDLE_B, HELMET_IDLE_A, HELMET_IDLE_B, HELMET_IDLE_A];
  const HEIGHT = HELMET_IDLE_A.length;

  for (let i = 0; i < frames.length; i++) {
    if (i > 0) {
      // Move cursor up to overwrite previous frame
      process.stdout.write(`\x1B[${HEIGHT}A`);
    }
    process.stdout.write(renderFrame(frames[i], chalk.cyan) + '\n');
    await new Promise<void>(resolve => setTimeout(resolve, 350));
  }
}
