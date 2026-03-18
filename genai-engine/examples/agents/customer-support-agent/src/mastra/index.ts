import { Mastra } from "@mastra/core/mastra";
import { LibSQLStore } from "@mastra/libsql";
import {
  customerSupportAgent,
  planAgent,
  websearchAgent,
  githubAgent,
  draftAgent,
  reviewAgent,
} from "./agents";
import { ConsoleLogger, LogLevel } from "@mastra/core/logger";
import { Observability } from "@mastra/observability";
import { ArthurExporter } from "@arthur-ai/observability-sdk/mastra";

const LOG_LEVEL = (process.env.LOG_LEVEL as LogLevel) || "info";

export const mastra = new Mastra({
  agents: {
    customerSupportAgent,
    planAgent,
    websearchAgent,
    githubAgent,
    draftAgent,
    reviewAgent,
  },
  storage: new LibSQLStore({
    id: "customer-support-agent",
    url: ":memory:",
  }),
  logger: new ConsoleLogger({
    level: LOG_LEVEL,
  }),
  observability: new Observability({
    configs: {
      arthur: {
        serviceName: "customer-support-agent",
        exporters: [
          new ArthurExporter({
            serviceName: "customer-support-agent",
            url: process.env.ARTHUR_BASE_URL!,
            apiKey: process.env.ARTHUR_API_KEY!,
            taskId: process.env.ARTHUR_TASK_ID!,
          }),
        ],
      },
    },
  }),
});
