/**
 * Test Harness for Customer Support Agent
 * 
 * This script reads questions from test-questions.json and sends them
 * to the customer support agent, logging results and traces.
 */

/**
 * Test Harness for Customer Support Agent
 * 
 * This script reads questions from test-questions.json and sends them
 * to the customer support agent, logging results and traces.
 * 
 * NOTE: This script expects environment variables to be already loaded
 * by the run-test.js loader script.
 */

import fs from "fs/promises";
import path from "path";
import { mastra } from "../src/mastra";
import { getTemplatedPrompt } from "../src/mastra/lib/arthur-api-client";
import { wrapMastra, getAITracing, AISpanType } from "@mastra/core/ai-tracing";
import { z } from "zod";

// Define schemas (same as in the API route)
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

interface TestQuestion {
  id: string;
  question: string;
  category?: string;
}

interface TestResult {
  questionId: string;
  question: string;
  category?: string;
  answer: string;
  sources: string[];
  completeness: string;
  metadata: {
    plan: string;
    searchesConducted: {
      docs: boolean;
      code: boolean;
    };
  };
  timestamp: string;
  durationMs?: number;
  error?: string;
}

async function processQuestion(question: TestQuestion): Promise<TestResult> {
  const startTime = Date.now();
  
  try {
    console.log(`\n${"=".repeat(80)}`);
    console.log(`Processing: ${question.id} - ${question.question}`);
    console.log("=".repeat(80));

    // Get the AI tracing instance from the global registry
    const aiTracing = getAITracing("arthur");
    if (!aiTracing) {
      throw new Error("Arthur AI tracing not configured");
    }

    // Create root span for this test question
    const rootSpan = aiTracing.startSpan({
      type: AISpanType.AGENT_RUN,
      name: `test-harness-${question.id}`,
      input: { 
        userQuestion: question.question,
        testQuestionId: question.id,
        category: question.category,
      },
      metadata: {
        testRun: true,
        questionId: question.id,
      },
    });

    const tracingContext = { currentSpan: rootSpan };
    const tracedMastra = wrapMastra(mastra, tracingContext);

    try {
      // Step 1: Plan
      console.log("Step 1: Creating plan...");
      const { messages: planMessages } = await getTemplatedPrompt({
        promptName: "mastra-agent-support-plan",
        promptVersion: "production",
        taskId: process.env.ARTHUR_TASK_ID!,
        variables: [{ name: "userQuestion", value: question.question }],
        tracingContext,
      });

      const planAgent = tracedMastra.getAgent("planAgent");
      const planResult = await planAgent.generate(planMessages, {
        output: PlanOutputSchema,
      });
      const plan = planResult.object;
      console.log(`Plan: ${plan.plan}`);
      console.log(`Needs docs: ${plan.needsDocs}, Needs code: ${plan.needsCode}`);

      // Steps 2-3: Parallel search
      console.log("\nSteps 2-3: Executing searches...");
      const searchPromises = [];
      let docsResults = null;
      let githubResults = null;

      if (plan.needsDocs && plan.docsQuery) {
        console.log(`  - Searching docs with query: "${plan.docsQuery}"`);
        searchPromises.push(
          (async () => {
            const { messages } = await getTemplatedPrompt({
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
            const result = await agent.generate(messages, { output: SearchOutputSchema });
            return { type: "docs", data: result.object };
          })()
        );
      }

      if (plan.needsCode && plan.codeQuery) {
        console.log(`  - Searching GitHub with query: "${plan.codeQuery}"`);
        searchPromises.push(
          (async () => {
            const { messages } = await getTemplatedPrompt({
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
            const result = await agent.generate(messages, { output: SearchOutputSchema });
            return { type: "github", data: result.object };
          })()
        );
      }

      const searchResults = await Promise.all(searchPromises);
      searchResults.forEach((r) => {
        if (r.type === "docs") {
          docsResults = r.data;
          console.log(`  ✓ Docs search completed: ${r.data.sources.length} sources`);
        }
        if (r.type === "github") {
          githubResults = r.data;
          console.log(`  ✓ GitHub search completed: ${r.data.sources.length} sources`);
        }
      });

      // Step 4: Draft
      console.log("\nStep 4: Drafting response...");
      const { messages: draftMessages } = await getTemplatedPrompt({
        promptName: "mastra-agent-support-draft",
        promptVersion: "production",
        taskId: process.env.ARTHUR_TASK_ID!,
        variables: [
          { name: "userQuestion", value: question.question },
          { name: "docsResults", value: docsResults ? JSON.stringify(docsResults) : "No documentation searched" },
          { name: "githubResults", value: githubResults ? JSON.stringify(githubResults) : "No code searched" },
        ],
        tracingContext,
      });

      const draftAgent = tracedMastra.getAgent("draftAgent");
      const draftResult = await draftAgent.generate(draftMessages, {
        output: DraftOutputSchema,
      });
      const draft = draftResult.object;
      console.log(`Draft confidence: ${draft.confidence}`);

      // Step 5: Review
      console.log("\nStep 5: Reviewing and finalizing...");
      const { messages: reviewMessages } = await getTemplatedPrompt({
        promptName: "mastra-agent-support-review",
        promptVersion: "production",
        taskId: process.env.ARTHUR_TASK_ID!,
        variables: [
          { name: "userQuestion", value: question.question },
          { name: "plan", value: plan.plan },
          { name: "draftResponse", value: JSON.stringify(draft) },
        ],
        tracingContext,
      });

      const reviewAgent = tracedMastra.getAgent("reviewAgent");
      const reviewResult = await reviewAgent.generate(reviewMessages, {
        output: ReviewOutputSchema,
      });
      const finalOutput = reviewResult.object;

      const durationMs = Date.now() - startTime;
      console.log(`\n✓ Completed in ${durationMs}ms`);
      console.log(`Completeness: ${finalOutput.completeness}`);
      console.log(`Sources: ${finalOutput.sources.length}`);

      // End the root span with success
      rootSpan.end({
        output: {
          finalResponse: finalOutput.finalResponse,
          sources: finalOutput.sources,
        },
      });

      return {
        questionId: question.id,
        question: question.question,
        category: question.category,
        answer: finalOutput.finalResponse,
        sources: finalOutput.sources,
        completeness: finalOutput.completeness,
        metadata: {
          plan: plan.plan,
          searchesConducted: {
            docs: plan.needsDocs,
            code: plan.needsCode,
          },
        },
        timestamp: new Date().toISOString(),
        durationMs,
      };
    } catch (error) {
      // End the root span with error
      rootSpan.error({
        error: error instanceof Error ? error : new Error(String(error)),
      });
      rootSpan.end();
      throw error;
    }
  } catch (error) {
    const durationMs = Date.now() - startTime;
    console.error(`✗ Error processing question ${question.id}:`, error);
    
    return {
      questionId: question.id,
      question: question.question,
      category: question.category,
      answer: "",
      sources: [],
      completeness: "error",
      metadata: {
        plan: "",
        searchesConducted: {
          docs: false,
          code: false,
        },
      },
      timestamp: new Date().toISOString(),
      durationMs,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function main() {
  console.log("Customer Support Agent Test Harness");
  console.log("====================================\n");

  // Load test questions
  const questionsPath = path.join(__dirname, "test-questions.json");
  console.log(`Loading questions from: ${questionsPath}`);
  
  const questionsData = await fs.readFile(questionsPath, "utf-8");
  const { questions } = JSON.parse(questionsData) as { questions: TestQuestion[] };
  
  console.log(`Loaded ${questions.length} test questions\n`);

  // Process each question
  const results: TestResult[] = [];
  
  for (const question of questions) {
    const result = await processQuestion(question);
    results.push(result);
    
    // Brief pause between questions
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // Generate summary
  console.log("\n" + "=".repeat(80));
  console.log("TEST RESULTS SUMMARY");
  console.log("=".repeat(80));
  
  const successful = results.filter(r => !r.error);
  const failed = results.filter(r => r.error);
  
  console.log(`\nTotal questions: ${results.length}`);
  console.log(`Successful: ${successful.length}`);
  console.log(`Failed: ${failed.length}`);
  
  if (successful.length > 0) {
    const avgDuration = successful.reduce((sum, r) => sum + (r.durationMs || 0), 0) / successful.length;
    console.log(`Average duration: ${avgDuration.toFixed(0)}ms`);
  }

  // Save results to file
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const resultsPath = path.join(__dirname, `test-results-${timestamp}.json`);
  await fs.writeFile(resultsPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to: ${resultsPath}`);

  // Print individual results
  console.log("\n" + "=".repeat(80));
  console.log("INDIVIDUAL RESULTS");
  console.log("=".repeat(80));
  
  for (const result of results) {
    console.log(`\n[${result.questionId}] ${result.question}`);
    if (result.error) {
      console.log(`  ✗ ERROR: ${result.error}`);
    } else {
      console.log(`  ✓ Answer: ${result.answer.substring(0, 200)}${result.answer.length > 200 ? "..." : ""}`);
      console.log(`  Completeness: ${result.completeness}`);
      console.log(`  Sources: ${result.sources.length}`);
      console.log(`  Duration: ${result.durationMs}ms`);
    }
  }

  console.log("\n" + "=".repeat(80));
  console.log("Test harness completed!");
  console.log("=".repeat(80));
  
  // Exit with error code if any tests failed
  process.exit(failed.length > 0 ? 1 : 0);
}

// Run the test harness
main().catch((error) => {
  console.error("Fatal error in test harness:", error);
  process.exit(1);
});
