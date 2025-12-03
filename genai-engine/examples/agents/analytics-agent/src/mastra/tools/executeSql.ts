import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { TracingContext } from "@mastra/core/ai-tracing";

export type ExecuteSqlToolResult = z.infer<typeof ExecuteSqlToolResultSchema>;

const ExecuteSqlToolResultSchema = z.object({
  data: z.object({
    columns: z.array(z.string()).describe("The names of the columns"),
    rows: z
      .array(z.array(z.union([z.string(), z.number(), z.boolean(), z.null()])))
      .describe(
        "The query results as an array of arrays, where each inner array represents a row and the values are in the order of the columns"
      ),
  }),
  rowCount: z.number().describe("The number of rows returned"),
  executionTime: z.number().describe("The execution time in milliseconds"),
  query: z.string().describe("The SQL query that was executed"),
});

export const executeSqlTool = createTool({
  id: "execute-sql",
  description: "Execute a PostgreSQL SQL query and return mock data results",
  inputSchema: z.object({
    sqlQuery: z.string().describe("The SQL query to execute"),
  }),
  outputSchema: ExecuteSqlToolResultSchema,
  execute: async ({ context, runtimeContext, mastra, tracingContext }) => {
    try {
      const agent = mastra?.getAgent("executeSqlAgent");
      if (!agent) {
        throw new Error("Execute SQL agent not found");
      }
      const messages = [{ role: "user" as const, content: context.sqlQuery }];
      const response = await agent.generate(messages, {
        output: ExecuteSqlToolResultSchema,
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
