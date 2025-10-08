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
  data: z.array(z.record(z.any())).describe("The processed data for the graph"),
  description: z.string().describe("Brief description of what the graph shows"),
});

export const generateGraphTool = createTool({
  id: "generate-graph",
  description: "Generate a graph visualization from SQL query results",
  inputSchema: z.object({
    sqlResults: z
      .array(z.record(z.any()))
      .describe(
        "The SQL query results to visualize. This should be the output of the executeSqlTool."
      ),
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
      const response = await agent.generateVNext(messages, {
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
