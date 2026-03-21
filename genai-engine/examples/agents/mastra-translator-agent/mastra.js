import { Mastra } from "@mastra/core/mastra";
import { Observability } from "@mastra/observability";
import { ArthurExporter } from "@arthur-ai/observability-sdk/mastra";
import { translatorAgent } from "./agent.js";

export const mastra = new Mastra({
  agents: { translatorAgent },
  observability: new Observability({
    configs: {
      arthur: {
        serviceName: "translator-agent",
        exporters: [
          new ArthurExporter({
            serviceName: "translator-agent",
            url: process.env.ARTHUR_BASE_URL,
            apiKey: process.env.ARTHUR_API_KEY,
            taskId: process.env.ARTHUR_TASK_ID,
          }),
        ],
      },
    },
  }),
});
