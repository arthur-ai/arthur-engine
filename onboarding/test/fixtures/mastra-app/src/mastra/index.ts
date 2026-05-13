/**
 * Minimal Mastra app — no Arthur exporter yet.
 * This is the fixture that Buzz E2E tests will instrument.
 */
import { Mastra } from '@mastra/core/mastra';
import { Agent } from '@mastra/core/agent';
import { openai } from '@ai-sdk/openai';

const greetingAgent = new Agent({
  name: 'greetingAgent',
  instructions: 'You are a friendly greeter.',
  model: openai('gpt-4o-mini'),
});

export const mastra = new Mastra({
  agents: { greetingAgent },
});
