/**
 * Minimal OpenAI JS app — no OpenInference yet.
 * Buzz E2E test fixture.
 */
import OpenAI from 'openai';

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

async function run() {
  const completion = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: 'Say hello in one sentence.' }],
  });
  console.log(completion.choices[0].message.content);
}

run().catch(console.error);
