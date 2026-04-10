import { translatorAgent } from "./agent.js";

const input = "Translate to French: Good morning! I hope you have a wonderful day.";

console.log("Input:", input);

const response = await translatorAgent.generate([
  { role: "user", content: input },
]);

console.log("Output:", response.text);
