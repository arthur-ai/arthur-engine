import { createTool } from "@mastra/core/tools";
import { z } from "zod";
import { AISpanType, TracingContext } from "@mastra/core/ai-tracing";

export type TextToSqlToolResult = z.infer<typeof TextToSqlToolResultSchema>;

// Mock RAG results for saved queries
const MOCK_RAG_RESULTS = [
  {
    metadata: {
      score: "0",
      distance: 0.4234567,
      certainty: 0.7891234567890123,
    },
    content: {
      question:
        "What is the conversion rate from lead to application by month for the last 6 months?",
      sql_query:
        'SELECT DATE_TRUNC(\'month\', "CreatedOn") AS month, COUNT(DISTINCT "LeadId") AS total_leads, COUNT(DISTINCT CASE WHEN "ApplicationDate" IS NOT NULL THEN "LeadId" END) AS applications, ROUND(COUNT(DISTINCT CASE WHEN "ApplicationDate" IS NOT NULL THEN "LeadId" END) * 100.0 / COUNT(DISTINCT "LeadId"), 2) AS conversion_rate FROM transactions."vw_LeadDetails" WHERE "Deleted" = FALSE AND "CreatedOn" >= CURRENT_DATE - INTERVAL \'6 months\' GROUP BY DATE_TRUNC(\'month\', "CreatedOn") ORDER BY month DESC',
    },
  },
  {
    metadata: {
      score: "0",
      distance: 0.5123456,
      certainty: 0.7567890123456789,
    },
    content: {
      question:
        "Show me the top 10 zip codes by number of settled loans and their average loan amounts",
      sql_query:
        'SELECT "ZipCode", COUNT(DISTINCT "LeadId") AS settled_loans, ROUND(AVG(COALESCE(NULLIF(REGEXP_REPLACE("LoanAmount"::text, \'[^0-9.\\-]\', \'\', \'g\'), \'\')::numeric, 0)), 2) AS avg_loan_amount FROM transactions."vw_LeadDetails" WHERE "Deleted" = FALSE AND ("StageKey" = \'settled\' OR "SettledDate" IS NOT NULL) AND "SettledDate" IS NOT NULL AND "ZipCode" IS NOT NULL GROUP BY "ZipCode" ORDER BY settled_loans DESC, avg_loan_amount DESC LIMIT 10',
    },
  },
  {
    metadata: {
      score: "0",
      distance: 0.6789012,
      certainty: 0.7234567890123456,
    },
    content: {
      question:
        "What is the average time to first contact after lead creation by lead source?",
      sql_query:
        'SELECT "LeadSource", COUNT(DISTINCT "LeadId") AS total_leads, ROUND(AVG(EXTRACT(EPOCH FROM ("FirstContactDate" - "CreatedOn")) / 3600.0), 2) AS avg_hours_to_contact FROM transactions."vw_LeadDetails" WHERE "Deleted" = FALSE AND "FirstContactDate" IS NOT NULL AND "CreatedOn" IS NOT NULL AND "LeadSource" IS NOT NULL AND "FirstContactDate" >= "CreatedOn" GROUP BY "LeadSource" ORDER BY avg_hours_to_contact ASC',
    },
  },
];

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
      // insert mock RAG span
      const ragSpan = tracingContext?.currentSpan?.createChildSpan({
        type: AISpanType.GENERIC,
        name: `rag-retrieval-savedQueries`,
        input: {
          className: "savedQueries",
          nearText: context.userQuery,
          limit: 10,
        },
        metadata: {
          type: "rag_retrieval",
          source: "weaviate",
        },
      });

      ragSpan?.end({
        output: {
          resultsCount: MOCK_RAG_RESULTS.length,
          results: MOCK_RAG_RESULTS,
        },
        metadata: {
          durationMs: 150,
          success: true,
        },
      });

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
