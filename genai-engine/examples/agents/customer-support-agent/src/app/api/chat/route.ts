import { NextRequest, NextResponse } from "next/server";
import { mastra } from "@/mastra";
import { getTemplatedPrompt } from "@/mastra/lib/arthur-api-client";
import { resolveModelFromPrompt } from "@/mastra/lib/model-resolver";
import { wrapMastra, getAITracing, AISpanType } from "@mastra/core/ai-tracing";
import { z } from "zod";

// Define schemas
const PlanOutputSchema = z.object({
  plan: z.string(),
  needsDocs: z.boolean(),
  needsCode: z.boolean(),
  docsQuery: z.string(),
  codeQuery: z.string(),
});

const SearchOutputSchema = z.object({
  summary: z.string(),
  relevantInfo: z.array(z.string()),
  sources: z.array(z.string()),
});

const DraftOutputSchema = z.object({
  response: z.string(),
  confidence: z.string(),
  sources: z.array(z.string()),
});

const ReviewOutputSchema = z.object({
  finalResponse: z.string(),
  completeness: z.string(),
  sources: z.array(z.string()),
});

export async function POST(req: NextRequest) {
  try {
    const { message } = await req.json();

    if (!message || typeof message !== "string") {
      return NextResponse.json(
        { error: "Message is required and must be a string" },
        { status: 400 }
      );
    }

    console.log("Processing customer support request:", message);

    // Get the AI tracing instance from the global registry
    const aiTracing = getAITracing("arthur");
    if (!aiTracing) {
      throw new Error("Arthur AI tracing not configured");
    }

    // Create root span for the entire customer support conversation
    const rootSpan = aiTracing.startSpan({
      type: AISpanType.AGENT_RUN,
      name: "customer-support-conversation",
      input: { userQuestion: message },
      metadata: {
        conversationType: "customer_support",
      },
    });

    // Create tracing context with the root span
    const tracingContext = { currentSpan: rootSpan };

    // Wrap mastra with the tracing context so all agent calls are nested
    const tracedMastra = wrapMastra(mastra, tracingContext);

    try {
      // Step 1: Plan
      console.log("Step 1: Creating plan...");
      const planPrompt = await getTemplatedPrompt({
        promptName: "mastra-agent-support-plan",
        promptVersion: "production",
        taskId: process.env.ARTHUR_TASK_ID!,
        variables: [{ name: "userQuestion", value: message }],
        tracingContext,
      });

      const planAgent = tracedMastra.getAgent("planAgent");
      const planResult = await planAgent.generate(planPrompt.messages, {
        output: PlanOutputSchema,
        model: resolveModelFromPrompt(planPrompt),
      });
      const plan = planResult.object;

    // Steps 2-3: Parallel search
    console.log("Steps 2-3: Executing searches...");
    const searchPromises = [];
    let docsResults = null;
    let githubResults = null;

    if (plan.needsDocs && plan.docsQuery) {
      searchPromises.push(
        (async () => {
          const websearchPrompt = await getTemplatedPrompt({
            promptName: "mastra-agent-support-websearch",
            promptVersion: "production",
            taskId: process.env.ARTHUR_TASK_ID!,
            variables: [
              { name: "searchQuery", value: plan.docsQuery },
              { name: "plan", value: plan.plan },
            ],
            tracingContext,
          });
          const agent = tracedMastra.getAgent("websearchAgent");
          const result = await agent.generate(websearchPrompt.messages, {
            output: SearchOutputSchema,
            model: resolveModelFromPrompt(websearchPrompt),
          });
          return { type: "docs", data: result.object };
        })()
      );
    }

    if (plan.needsCode && plan.codeQuery) {
      searchPromises.push(
        (async () => {
          const githubPrompt = await getTemplatedPrompt({
            promptName: "mastra-agent-support-github",
            promptVersion: "production",
            taskId: process.env.ARTHUR_TASK_ID!,
            variables: [
              { name: "searchQuery", value: plan.codeQuery },
              { name: "plan", value: plan.plan },
            ],
            tracingContext,
          });
          const agent = tracedMastra.getAgent("githubAgent");
          const result = await agent.generate(githubPrompt.messages, {
            output: SearchOutputSchema,
            model: resolveModelFromPrompt(githubPrompt),
          });
          return { type: "github", data: result.object };
        })()
      );
    }

    const searchResults = await Promise.all(searchPromises);
    searchResults.forEach((r) => {
      if (r.type === "docs") docsResults = r.data;
      if (r.type === "github") githubResults = r.data;
    });

      // Step 4: Draft
      console.log("Step 4: Drafting response...");
      const draftPrompt = await getTemplatedPrompt({
        promptName: "mastra-agent-support-draft",
        promptVersion: "production",
        taskId: process.env.ARTHUR_TASK_ID!,
        variables: [
          { name: "userQuestion", value: message },
          { name: "docsResults", value: docsResults ? JSON.stringify(docsResults) : "No documentation searched" },
          { name: "githubResults", value: githubResults ? JSON.stringify(githubResults) : "No code searched" },
        ],
        tracingContext,
      });

      const draftAgent = tracedMastra.getAgent("draftAgent");
      const draftResult = await draftAgent.generate(draftPrompt.messages, {
        output: DraftOutputSchema,
        model: resolveModelFromPrompt(draftPrompt),
      });
      const draft = draftResult.object;

      // Step 5: Review
      console.log("Step 5: Reviewing and finalizing...");
      const reviewPrompt = await getTemplatedPrompt({
        promptName: "mastra-agent-support-review",
        promptVersion: "production",
        taskId: process.env.ARTHUR_TASK_ID!,
        variables: [
          { name: "userQuestion", value: message },
          { name: "plan", value: plan.plan },
          { name: "draftResponse", value: JSON.stringify(draft) },
        ],
        tracingContext,
      });

      const reviewAgent = tracedMastra.getAgent("reviewAgent");
      const reviewResult = await reviewAgent.generate(reviewPrompt.messages, {
        output: ReviewOutputSchema,
        model: resolveModelFromPrompt(reviewPrompt),
      });
      const finalOutput = reviewResult.object;

      console.log("Request completed");

      // Ensure sources is always an array
      const sources = finalOutput.sources ?? [];

      // End the root span with the final output
      rootSpan.end({
        output: {
          finalResponse: finalOutput.finalResponse,
          sources: sources,
        },
      });

      return NextResponse.json({
        answer: finalOutput.finalResponse,
        sources: sources,
        completeness: finalOutput.completeness,
        metadata: {
          plan: plan.plan,
          searchesConducted: {
            docs: plan.needsDocs,
            code: plan.needsCode,
          },
        },
      });
    } catch (error) {
      // End the root span with error
      rootSpan.error({
        error: error instanceof Error ? error : new Error(String(error)),
      });
      rootSpan.end();
      throw error;
    }
  } catch (error) {
    console.error("Error in chat route:", error);
    return NextResponse.json(
      {
        error: "An error occurred while processing your request",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 }
    );
  }
}
