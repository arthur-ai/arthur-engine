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
import { ArthurExporter } from "./observability/arthur";

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
    url: ":memory:",
  }),
  logger: new ConsoleLogger({
    level: LOG_LEVEL,
  }),
  observability: {
    configs: {
      arthur: {
        serviceName: "ai",
        exporters: [
          new ArthurExporter({
            serviceName: "customer-support-agent",
            url: process.env.ARTHUR_BASE_URL!,
            headers: {
              Authorization: `Bearer ${process.env.ARTHUR_API_KEY!}`,
            },
            taskId: process.env.ARTHUR_TASK_ID!,
          }),
        ],
      },
    },
  },
});
