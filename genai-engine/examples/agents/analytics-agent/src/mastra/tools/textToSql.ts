import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { openai } from "@ai-sdk/openai";
import { TracingContext } from "@mastra/core/ai-tracing";
import { MastraLLMVNext } from "@mastra/core/llm/model/model.loop";

export type TextToSqlToolResult = z.infer<typeof TextToSqlToolResultSchema>;

const TextToSqlToolResultSchema = z.object({
  sqlQuery: z.string().describe("The generated PostgreSQL SQL query"),
  explanation: z
    .string()
    .describe("Brief explanation of what the SQL query does"),
});

export const textToSqlTool = createTool({
  id: "text-to-sql",
  description:
    "Convert natural language queries into PostgreSQL SQL statements",
  inputSchema: z.object({
    userQuery: z
      .string()
      .describe("The user's natural language query to convert to SQL"),
  }),
  outputSchema: TextToSqlToolResultSchema,
  execute: async ({ context, runtimeContext, mastra, tracingContext }) => {
    try {
      const agent = mastra?.getAgent("textToSqlAgent");
      if (!agent) {
        throw new Error("Text to sql agent not found");
      }
      const messages = [{ role: "user" as const, content: context.userQuery }];
      const response = await agent.generateVNext(messages, {
        output: TextToSqlToolResultSchema,
        runtimeContext,
        tracingContext: tracingContext as TracingContext,
      });

      return response.object;
    } catch (error) {
      console.error(error);
      throw error;
    }
  },
});
