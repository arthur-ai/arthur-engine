import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { openai } from "@ai-sdk/openai";
import { MastraLLMV1 } from "@mastra/core/llm/model";
import { TracingContext } from "@mastra/core/ai-tracing";

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
    const systemPrompt = `You are an expert SQL developer specializing in PostgreSQL. 
Your task is to convert natural language queries into valid PostgreSQL SQL statements.

Do not ask the user for clarifications or schema definitions. When in doubt, assume a 
schema that would make sense for the user's query. It's more important to return plausible SQL
than to be completely accurate.

Guidelines:
- Always generate valid PostgreSQL syntax
- Use appropriate data types and functions
- Include proper WHERE clauses, JOINs, and aggregations as needed
- Be conservative with assumptions about table/column names
- If the query is ambiguous, make reasonable assumptions and note them
- Always return a valid SQL statement that can be executed

Return your response in the following JSON format:
{
  "sqlQuery": "SELECT * FROM table_name WHERE condition;",
  "explanation": "Brief explanation of what this query does"
}`;

    try {
      const agent = mastra?.getAgent("analystAgent");
      if (!agent) {
        throw new Error("Analyst agent not found");
      }
      const llm = (await agent.getLLM({
        runtimeContext,
        model: openai("gpt-4.1"),
      })) as MastraLLMV1;
      const fullPrompt = `${systemPrompt}\n\nUser query: ${context.userQuery}`;
      const response = await llm.generate(fullPrompt, {
        output: TextToSqlToolResultSchema,
        runtimeContext,
        tracingContext: tracingContext as TracingContext,
        mode: "json",
      });

      return response.object;
    } catch (error) {
      throw new Error(
        `Failed to generate SQL query: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  },
});
