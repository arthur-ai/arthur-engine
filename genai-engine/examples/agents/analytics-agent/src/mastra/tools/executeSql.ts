import { createTool } from "@mastra/core/tools";
import { Agent } from "@mastra/core/agent";
import { z } from "zod";
import { TracingContext } from "@mastra/core/ai-tracing";
import { checkArthurGuardrails } from "./arthurGuardrail";

const GUARDRAILS_ENABLED =
  process.env.ARTHUR_GUARDRAILS_ENABLED?.toLowerCase() === "true";
const SIMULATE_HALLUCINATION =
  process.env.SIMULATE_HALLUCINATION?.toLowerCase() === "true";
const MAX_GUARDRAIL_RETRIES = 4;

const SqlDataSchema = z.object({
  columns: z.array(z.string()).describe("The names of the columns"),
  rows: z
    .array(z.array(z.union([z.string(), z.number(), z.boolean(), z.null()])))
    .describe(
      "The query results as an array of arrays, where each inner array represents a row and the values are in the order of the columns"
    ),
});

const GuardrailAttemptSchema = z.object({
  attempt: z.number(),
  blocked: z.boolean(),
  inferenceId: z.string(),
  blockedReason: z.string().optional(),
  validatedResponse: z.string(),
});

const GuardrailResultSchema = z.object({
  finalBlocked: z.boolean(),
  totalAttempts: z.number(),
  blockedReason: z.string().optional(),
  attempts: z.array(GuardrailAttemptSchema),
});

export type ExecuteSqlToolResult = z.infer<typeof ExecuteSqlToolResultSchema>;

const ExecuteSqlToolResultSchema = z.object({
  data: SqlDataSchema,
  rowCount: z.number().describe("The number of rows returned"),
  executionTime: z.number().describe("The execution time in milliseconds"),
  query: z.string().describe("The SQL query that was executed"),
  /** Present only when ARTHUR_GUARDRAILS_ENABLED=true */
  guardrailResult: GuardrailResultSchema.optional(),
});

const SummaryResponseSchema = z.object({
  summary: z.string().describe("Natural language summary of the SQL results"),
});

/**
 * Asks the generateSqlSummaryAgent to produce a natural language summary of
 * the SQL results. On retries, the previousBlockedReason is included so the
 * LLM can self-correct.
 *
 * In simulation mode the very first call asks the LLM to inflate numbers,
 * triggering Arthur's hallucination rule so the retry flow can be demonstrated.
 */
async function generateSummary(
  data: z.infer<typeof SqlDataSchema>,
  query: string,
  agent: Agent,
  runtimeContext: any,
  tracingContext: TracingContext | undefined,
  isFirstSimulationAttempt: boolean,
  previousBlockedReason?: string
): Promise<string> {
  const dataJson = JSON.stringify({ columns: data.columns, rows: data.rows });

  let userMessage: string;
  if (previousBlockedReason) {
    userMessage =
      `The following SQL query was run:\n${query}\n\n` +
      `Results:\n${dataJson}\n\n` +
      `Your previous summary was rejected by a guardrail with this reason:\n` +
      `"${previousBlockedReason}"\n\n` +
      `Please produce a corrected, accurate summary that addresses this issue.`;
  } else if (isFirstSimulationAttempt) {
    userMessage =
      `The following SQL query was run:\n${query}\n\n` +
      `Results:\n${dataJson}\n\n` +
      `[SIMULATION] Summarise the results but inflate all numeric values by approximately 7x to simulate a hallucinating model.`;
  } else {
    userMessage =
      `The following SQL query was run:\n${query}\n\n` +
      `Results:\n${dataJson}\n\n` +
      `Please summarise these results accurately.`;
  }

  const response = await agent.generate(
    [{ role: "user" as const, content: userMessage }],
    { output: SummaryResponseSchema, runtimeContext, tracingContext }
  );
  return response.object.summary;
}

export const executeSqlTool = createTool({
  id: "execute-sql",
  description: "Execute a PostgreSQL SQL query and return mock data results",
  inputSchema: z.object({
    sqlQuery: z.string().describe("The SQL query to execute"),
  }),
  outputSchema: ExecuteSqlToolResultSchema,
  execute: async ({ context, runtimeContext, mastra, tracingContext }) => {
    // Step 1 — generate the structured SQL data (ground truth)
    const sqlAgent = mastra?.getAgent("executeSqlAgent");
    if (!sqlAgent) throw new Error("Execute SQL agent not found");

    const sqlResponse = await sqlAgent.generate(
      [{ role: "user" as const, content: context.sqlQuery }],
      {
        output: ExecuteSqlToolResultSchema.omit({ guardrailResult: true }),
        runtimeContext,
        tracingContext: tracingContext as TracingContext,
      }
    );
    const realData = sqlResponse.object;

    if (!GUARDRAILS_ENABLED) {
      return realData;
    }

    // Step 2 — retry loop: generate a summary and validate it with Arthur.
    // Each blocked attempt feeds the blockedReason back to the summary agent
    // so it can self-correct on the next try.
    const summaryAgent = mastra?.getAgent("generateSqlSummaryAgent") as Agent | undefined;
    if (!summaryAgent) throw new Error("generateSqlSummaryAgent not found");

    const attempts: z.infer<typeof GuardrailAttemptSchema>[] = [];
    let previousBlockedReason: string | undefined;

    for (let attempt = 1; attempt <= MAX_GUARDRAIL_RETRIES; attempt++) {
      const isFirstSimAttempt = SIMULATE_HALLUCINATION && attempt === 1;

      const summary = await generateSummary(
        realData.data,
        realData.query,
        summaryAgent,
        runtimeContext,
        tracingContext as TracingContext | undefined,
        isFirstSimAttempt,
        previousBlockedReason
      );

      const guardrailCheck = await checkArthurGuardrails(
        context.sqlQuery,
        summary,
        JSON.stringify(realData.data),
        tracingContext as TracingContext,
        `Guardrail (attempt ${attempt})`
      );

      attempts.push({
        attempt,
        blocked: guardrailCheck.blocked,
        inferenceId: guardrailCheck.inferenceId,
        blockedReason: guardrailCheck.blockedReason,
        validatedResponse: summary,
      });

      if (!guardrailCheck.blocked) {
        return {
          ...realData,
          guardrailResult: {
            finalBlocked: false,
            totalAttempts: attempt,
            attempts,
          },
        };
      }

      previousBlockedReason = guardrailCheck.blockedReason;
    }

    // All retries exhausted — return with the last blocked reason
    return {
      ...realData,
      guardrailResult: {
        finalBlocked: true,
        totalAttempts: MAX_GUARDRAIL_RETRIES,
        blockedReason: previousBlockedReason,
        attempts,
      },
    };
  },
});
