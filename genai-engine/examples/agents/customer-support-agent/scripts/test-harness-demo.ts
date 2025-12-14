/**
 * Demo Test Harness for Customer Support Agent
 * 
 * This script runs 100 inferences through the agent with backdated timestamps
 * to create a demo dataset with 10 inferences per day over 10 days.
 * 
 * NOTE: This script expects environment variables to be already loaded
 * by the run-test.js loader script.
 */

import fs from "fs/promises";
import path from "path";
import { mastra } from "../src/mastra";
import { getTemplatedPrompt } from "../src/mastra/lib/arthur-api-client";
import { resolveModelFromPrompt } from "../src/mastra/lib/model-resolver";
import { wrapMastra, getAITracing, AISpanType, shutdownAITracingRegistry } from "@mastra/core/ai-tracing";
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
  runNumber: number;
  dayNumber: number;
}

/**
 * Temporarily override Date to return a specific timestamp
 */
class DateOverride {
  private originalDate: DateConstructor;
  private targetTimestamp: number;

  constructor(targetDate: Date) {
    this.originalDate = Date;
    this.targetTimestamp = targetDate.getTime();
    
    // Override Date constructor and Date.now()
    const targetTimestamp = this.targetTimestamp;
    const OriginalDate = this.originalDate;
    
    (global as any).Date = class extends OriginalDate {
      constructor(...args: any[]) {
        if (args.length === 0) {
          super(targetTimestamp);
        } else {
          super(...args);
        }
      }
      
      static now() {
        return targetTimestamp;
      }
      
      // Copy all static methods from original Date
      static parse = OriginalDate.parse;
      static UTC = OriginalDate.UTC;
    } as any;
  }

  restore() {
    (global as any).Date = this.originalDate;
  }
}

async function processQuestion(
  question: TestQuestion, 
  runNumber: number,
  dayNumber: number,
  targetDate: Date
): Promise<TestResult> {
  const dateOverride = new DateOverride(targetDate);
  
  try {
    const startTime = Date.now();
    
    console.log(`\n${"=".repeat(80)}`);
    console.log(`[Run ${runNumber}/100] [Day ${dayNumber + 1}] Processing: ${question.id}`);
    console.log(`Target timestamp: ${new Date().toISOString()}`);
    console.log("=".repeat(80));

    // Get the AI tracing instance from the global registry
    const aiTracing = getAITracing("arthur");
    if (!aiTracing) {
      throw new Error("Arthur AI tracing not configured");
    }

    // Create root span for this test question
    const rootSpan = aiTracing.startSpan({
      type: AISpanType.AGENT_RUN,
      name: `demo-run-${runNumber}-${question.id}`,
      input: { 
        userQuestion: question.question,
        testQuestionId: question.id,
        category: question.category,
        runNumber: runNumber,
        dayNumber: dayNumber + 1,
      },
      metadata: {
        demoRun: true,
        runNumber: runNumber,
        dayNumber: dayNumber + 1,
        questionId: question.id,
      },
    });

    const tracingContext = { currentSpan: rootSpan };
    const tracedMastra = wrapMastra(mastra, tracingContext);

    try {
      // Step 1: Plan
      console.log("Step 1: Creating plan...");
      const planPrompt = await getTemplatedPrompt({
        promptName: "mastra-agent-support-plan",
        promptVersion: "production",
        taskId: process.env.ARTHUR_TASK_ID!,
        variables: [{ name: "userQuestion", value: question.question }],
        tracingContext,
      });

      const planAgent = tracedMastra.getAgent("planAgent");
      const planResult = await planAgent.generate(planPrompt.messages, {
        output: PlanOutputSchema,
        model: resolveModelFromPrompt(planPrompt),
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
        console.log(`  - Searching GitHub with query: "${plan.codeQuery}"`);
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
      const draftPrompt = await getTemplatedPrompt({
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
      const draftResult = await draftAgent.generate(draftPrompt.messages, {
        output: DraftOutputSchema,
        model: resolveModelFromPrompt(draftPrompt),
      });
      const draft = draftResult.object;
      console.log(`Draft confidence: ${draft.confidence}`);

      // Step 5: Review
      console.log("\nStep 5: Reviewing and finalizing...");
      const reviewPrompt = await getTemplatedPrompt({
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
      const reviewResult = await reviewAgent.generate(reviewPrompt.messages, {
        output: ReviewOutputSchema,
        model: resolveModelFromPrompt(reviewPrompt),
      });
      const finalOutput = reviewResult.object;

      const durationMs = Date.now() - startTime;
      console.log(`\n✓ Completed in ${durationMs}ms`);
      console.log(`Completeness: ${finalOutput.completeness}`);
      console.log(`Sources: ${finalOutput.sources?.length ?? 0}`);

      // Ensure sources is always an array
      const sources = finalOutput.sources ?? [];

      // End the root span with success
      rootSpan.end({
        output: {
          finalResponse: finalOutput.finalResponse,
          sources: sources,
        },
      });

      return {
        questionId: question.id,
        question: question.question,
        category: question.category,
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
        timestamp: new Date().toISOString(),
        durationMs,
        runNumber,
        dayNumber: dayNumber + 1,
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
      durationMs: 0,
      error: error instanceof Error ? error.message : String(error),
      runNumber,
      dayNumber: dayNumber + 1,
    };
  } finally {
    dateOverride.restore();
  }
}

async function main() {
  console.log("Customer Support Agent Demo Test Harness");
  console.log("==========================================");
  console.log("Running 100 inferences with backdated timestamps");
  console.log("10 inferences per day for 10 days\n");

  // Load test questions
  const questionsPath = path.join(__dirname, "test-questions.json");
  console.log(`Loading questions from: ${questionsPath}`);
  
  const questionsData = await fs.readFile(questionsPath, "utf-8");
  const { questions } = JSON.parse(questionsData) as { questions: TestQuestion[] };
  
  console.log(`Loaded ${questions.length} test questions`);
  console.log(`Will run ${questions.length} questions x 10 times = ${questions.length * 10} total inferences\n`);

  // Today's date at start of day
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Process 100 questions (10 loops of 10 questions)
  const results: TestResult[] = [];
  const TOTAL_RUNS = 100;
  const RUNS_PER_DAY = 10;
  const TOTAL_DAYS = TOTAL_RUNS / RUNS_PER_DAY;
  
  let runNumber = 1;
  
  for (let dayOffset = 0; dayOffset < TOTAL_DAYS; dayOffset++) {
    // Calculate the target date (going backwards from today)
    const targetDate = new Date(today);
    targetDate.setDate(targetDate.getDate() - (TOTAL_DAYS - 1 - dayOffset));
    
    console.log(`\n${"=".repeat(80)}`);
    console.log(`DAY ${dayOffset + 1} - ${targetDate.toDateString()}`);
    console.log("=".repeat(80));
    
    // Run 10 questions for this day
    for (let questionIdx = 0; questionIdx < RUNS_PER_DAY; questionIdx++) {
      const question = questions[questionIdx % questions.length];
      
      // Add some time variation within the day (spread across 12 hours)
      const targetDateTime = new Date(targetDate);
      targetDateTime.setHours(8); // Start at 8am
      targetDateTime.setMinutes(questionIdx * 72); // Spread across 12 hours (720 minutes / 10 = 72 minutes apart)
      
      const result = await processQuestion(question, runNumber, dayOffset, targetDateTime);
      results.push(result);
      runNumber++;
      
      // Brief pause between questions
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  // Generate summary
  console.log("\n" + "=".repeat(80));
  console.log("DEMO TEST RESULTS SUMMARY");
  console.log("=".repeat(80));
  
  const successful = results.filter(r => !r.error);
  const failed = results.filter(r => r.error);
  
  console.log(`\nTotal inferences: ${results.length}`);
  console.log(`Successful: ${successful.length}`);
  console.log(`Failed: ${failed.length}`);
  console.log(`Days simulated: ${TOTAL_DAYS}`);
  console.log(`Inferences per day: ${RUNS_PER_DAY}`);
  
  if (successful.length > 0) {
    const avgDuration = successful.reduce((sum, r) => sum + (r.durationMs || 0), 0) / successful.length;
    console.log(`Average duration: ${avgDuration.toFixed(0)}ms`);
  }

  // Group results by day
  const resultsByDay = new Map<number, TestResult[]>();
  results.forEach(r => {
    if (!resultsByDay.has(r.dayNumber)) {
      resultsByDay.set(r.dayNumber, []);
    }
    resultsByDay.get(r.dayNumber)!.push(r);
  });

  console.log("\n" + "=".repeat(80));
  console.log("RESULTS BY DAY");
  console.log("=".repeat(80));
  
  for (let day = 1; day <= TOTAL_DAYS; day++) {
    const dayResults = resultsByDay.get(day) || [];
    const daySuccessful = dayResults.filter(r => !r.error).length;
    const dayFailed = dayResults.filter(r => r.error).length;
    
    // Get the actual date for this day
    const targetDate = new Date(today);
    targetDate.setDate(targetDate.getDate() - (TOTAL_DAYS - day));
    
    console.log(`\nDay ${day} (${targetDate.toDateString()}): ${dayResults.length} runs`);
    console.log(`  Successful: ${daySuccessful}, Failed: ${dayFailed}`);
    
    if (dayResults.length > 0) {
      const firstTimestamp = new Date(dayResults[0].timestamp);
      const lastTimestamp = new Date(dayResults[dayResults.length - 1].timestamp);
      console.log(`  Time range: ${firstTimestamp.toLocaleTimeString()} - ${lastTimestamp.toLocaleTimeString()}`);
    }
  }

  // Save results to file
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const resultsPath = path.join(__dirname, `demo-results-${timestamp}.json`);
  await fs.writeFile(resultsPath, JSON.stringify(results, null, 2));
  console.log(`\n${"=".repeat(80)}`);
  console.log(`Results saved to: ${resultsPath}`);
  console.log("=".repeat(80));
  
  // Gracefully shutdown AI tracing to flush all spans
  console.log("\nFlushing traces to Arthur...");
  await shutdownAITracingRegistry();
  console.log("✓ All traces flushed successfully");
  
  // Exit with error code if any tests failed
  process.exit(failed.length > 0 ? 1 : 0);
}

// Run the test harness
main().catch(async (error) => {
  console.error("Fatal error in demo test harness:", error);
  
  // Attempt to flush traces even on error
  try {
    console.log("\nAttempting to flush traces...");
    await shutdownAITracingRegistry();
  } catch (shutdownError) {
    console.error("Error during trace shutdown:", shutdownError);
  }
  
  process.exit(1);
});
