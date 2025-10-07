import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { textToSqlTool } from "@/mastra/tools";
import { LibSQLStore } from "@mastra/libsql";
import { z } from "zod";
import { Memory } from "@mastra/memory";

export const AgentState = z.object({
  proverbs: z.array(z.string()).default([]),
});

export const dataAnalystAgent = new Agent({
  name: "dataAnalystAgent",
  tools: { textToSqlTool },
  model: openai("gpt-4.1"),
  instructions: "You are a helpful data analyst assistant.",
  memory: new Memory({
    storage: new LibSQLStore({ url: "file::memory:" }),
    options: {
      workingMemory: {
        enabled: true,
        schema: AgentState,
      },
    },
  }),
});
