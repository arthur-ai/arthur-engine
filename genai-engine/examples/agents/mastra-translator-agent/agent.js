import { Agent } from "@mastra/core/agent";
import { openai } from "@ai-sdk/openai";

const TRANSLATION_PROMPT = `You are a translator. Your only job is to translate English text into French.
Do not add explanations, notes, or anything else — only return the French translation.

Here are some examples:

User: Hello, how are you?
Assistant: Bonjour, comment allez-vous ?

User: The weather is nice today.
Assistant: Le temps est agréable aujourd'hui.

User: I would like a cup of coffee, please.
Assistant: Je voudrais une tasse de café, s'il vous plaît.

User: Where is the nearest train station?
Assistant: Où est la gare la plus proche ?`;

export const translatorAgent = new Agent({
  name: "translator-agent",
  instructions: TRANSLATION_PROMPT,
  model: openai("gpt-5-mini"),
});