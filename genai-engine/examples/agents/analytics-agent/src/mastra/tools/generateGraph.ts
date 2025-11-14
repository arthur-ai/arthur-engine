import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { TracingContext } from "@mastra/core/ai-tracing";

export type GenerateGraphToolResult = z.infer<
  typeof GenerateGraphToolResultSchema
>;

const GenerateGraphToolResultSchema = z.object({
  graphType: z
    .enum(["bar", "line", "pie", "scatter", "area"])
    .describe("The type of graph to render"),
  title: z.string().describe("The title of the graph"),
  xAxis: z.string().describe("The field to use for the x-axis"),
  yAxis: z.string().describe("The field to use for the y-axis"),
  data: z.object({
    columns: z.array(z.string()).describe("The names of the columns"),
    rows: z
      .array(z.array(z.union([z.string(), z.number(), z.boolean(), z.null()])))
      .describe(
        "The query results as an array of arrays, where each inner array represents a row and the values are in the order of the columns"
      ),
  }),
  description: z.string().describe("Brief description of what the graph shows"),
});

export const generateGraphTool = createTool({
  id: "generate-graph",
  description:
    "Generate a graph visualization from SQL query results. Make sure to include both the sqlResults and sqlQuery in the arguments.",
  inputSchema: z.object({
    sqlResults: z.object({
      columns: z.array(z.string()).describe("The names of the columns"),
      rows: z
        .array(
          z.array(z.union([z.string(), z.number(), z.boolean(), z.null()]))
        )
        .describe(
          "The query results as an array of arrays, where each inner array represents a row and the values are in the order of the columns"
        ),
    }),
    sqlQuery: z
      .string()
      .describe("The original SQL query that generated the results"),
  }),
  outputSchema: GenerateGraphToolResultSchema,
  execute: async ({ context, runtimeContext, mastra, tracingContext }) => {
    try {
      const agent = mastra?.getAgent("generateGraphAgent");
      if (!agent) {
        throw new Error("Generate graph agent not found");
      }
      const messages = [
        {
          role: "user" as const,
          content: `SQL Query: ${context.sqlQuery}\n\nResults: ${JSON.stringify(context.sqlResults, null, 2)}`,
        },
      ];
      const response = await agent.generate(messages, {
        output: GenerateGraphToolResultSchema,
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
