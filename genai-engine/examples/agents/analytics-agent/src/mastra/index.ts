import { Mastra } from "@mastra/core/mastra";
import { LibSQLStore } from "@mastra/libsql";
import {
  dataAnalystAgent,
  textToSqlAgent,
  executeSqlAgent,
  generateGraphAgent,
} from "./agents";
import { ConsoleLogger, LogLevel } from "@mastra/core/logger";
import { ArthurExporter } from "./observability/arthur";
import { ContextAwareMastraAgent } from "./agents/context-aware-agent";

const LOG_LEVEL = (process.env.LOG_LEVEL as LogLevel) || "info";

// Create the exporter instance
const arthurExporter = new ArthurExporter({
  serviceName: "analytics-agent",
  url: process.env.ARTHUR_BASE_URL!,
  headers: {
    Authorization: `Bearer ${process.env.ARTHUR_API_KEY!}`,
  },
  taskId: process.env.ARTHUR_TASK_ID!,
});

export const mastra = new Mastra({
  agents: {
    dataAnalystAgent,
    textToSqlAgent,
    executeSqlAgent,
    generateGraphAgent,
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
        exporters: [arthurExporter],
      },
    },
  },
});

// Export the exporter for access in API routes
export { arthurExporter, ContextAwareMastraAgent };
