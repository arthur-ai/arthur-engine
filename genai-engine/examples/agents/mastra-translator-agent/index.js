import { mastra } from "./mastra.js";

const input = "Translate to French: Good morning! I hope you have a wonderful day.";

console.log("Input:", input);

const agent = mastra.getAgent("translatorAgent");
const response = await agent.generate([
  { role: "user", content: input },
]);

console.log("Output:", response.text);
