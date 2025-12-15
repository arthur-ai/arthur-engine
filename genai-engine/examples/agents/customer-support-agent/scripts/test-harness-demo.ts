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
 * Temporarily override Date to return backdated timestamps while preserving elapsed time
 * 
 * This class calculates a time offset between the target (backdated) time and real time,
 * then applies that offset to all Date operations. This ensures:
 * - Start times are backdated to the target date
 * - End times are also backdated but preserve the actual elapsed duration
 * - Time progresses naturally during the inference run
 */
class DateOverride {
  private originalDate: DateConstructor;
  private timeOffset: number;

  constructor(targetDate: Date) {
    this.originalDate = Date;
    
    // Calculate the offset: target time - current real time
    // This offset will be added to all timestamps
    const realNow = this.originalDate.now();
    const targetTimestamp = targetDate.getTime();
    this.timeOffset = targetTimestamp - realNow;
    
    // Override Date constructor and Date.now()
    const timeOffset = this.timeOffset;
    const OriginalDate = this.originalDate;
    
    (global as any).Date = class extends OriginalDate {
      constructor(...args: any[]) {
        if (args.length === 0) {
          // Apply offset to current time
          super(OriginalDate.now() + timeOffset);
        } else {
          super(...args);
        }
      }
      
      static now() {
        // Apply offset to current real time
        return OriginalDate.now() + timeOffset;
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

      // Steps 2-3: Parallel search
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
        if (r.type === "docs") {
          docsResults = r.data;
        }
        if (r.type === "github") {
          githubResults = r.data;
        }
      });

      // Step 4: Draft
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

      // Step 5: Review
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

/**
 * Semaphore for limiting concurrent operations
 */
class Semaphore {
  private permits: number;
  private waiting: Array<() => void> = [];

  constructor(permits: number) {
    this.permits = permits;
  }

  async acquire(): Promise<void> {
    if (this.permits > 0) {
      this.permits--;
      return Promise.resolve();
    }

    return new Promise<void>((resolve) => {
      this.waiting.push(resolve);
    });
  }

  release(): void {
    this.permits++;
    if (this.waiting.length > 0) {
      const resolve = this.waiting.shift()!;
      this.permits--;
      resolve();
    }
  }

  async use<T>(fn: () => Promise<T>): Promise<T> {
    await this.acquire();
    try {
      return await fn();
    } finally {
      this.release();
    }
  }
}

async function main() {
  console.log("Customer Support Agent Demo Test Harness");
  console.log("==========================================");
  
  // ==================== CONFIGURATION ====================
  // Set this to resume from a specific day (1-10)
  // Set to 1 to start from the beginning
  const START_FROM_DAY = 1; // <-- CHANGE THIS TO RESUME FROM A DIFFERENT DAY
  
  // Set the number of parallel inferences to run at once
  // Higher = faster, but risks rate limiting
  // Recommended: 3-5 for most APIs, 1-2 for strict rate limits
  const PARALLEL_INFERENCES = 5; // <-- CHANGE THIS TO CONTROL CONCURRENCY
  // =======================================================
  
  console.log("Running 100 inferences with backdated timestamps");
  console.log("10 inferences per day for 10 days");
  console.log(`Parallelization: ${PARALLEL_INFERENCES} concurrent inferences`);
  if (START_FROM_DAY > 1) {
    console.log(`\n⚠️  RESUMING FROM DAY ${START_FROM_DAY} (skipping days 1-${START_FROM_DAY - 1})`);
  }
  console.log("");

  // Load test questions
  const questionsPath = path.join(__dirname, "test-questions.json");
  console.log(`Loading questions from: ${questionsPath}`);
  
  const questionsData = await fs.readFile(questionsPath, "utf-8");
  const { questions } = JSON.parse(questionsData) as { questions: TestQuestion[] };
  
  console.log(`Loaded ${questions.length} test questions`);
  
  // Today's date at start of day
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Process 100 questions (10 loops of 10 questions)
  const results: TestResult[] = [];
  const TOTAL_RUNS = 100;
  const RUNS_PER_DAY = 10;
  const TOTAL_DAYS = TOTAL_RUNS / RUNS_PER_DAY;
  
  // Calculate starting day offset (0-based)
  const startDayOffset = START_FROM_DAY - 1;
  
  // Calculate starting run number based on which day we're starting from
  let runNumber = (startDayOffset * RUNS_PER_DAY) + 1;
  
  const runsToComplete = (TOTAL_DAYS - startDayOffset) * RUNS_PER_DAY;
  console.log(`Will run ${runsToComplete} inferences (days ${START_FROM_DAY}-${TOTAL_DAYS})\n`);
  
  // Create semaphore to limit concurrency
  const semaphore = new Semaphore(PARALLEL_INFERENCES);
  
  // Track progress
  let completedRuns = 0;
  const startTime = Date.now();
  
  for (let dayOffset = startDayOffset; dayOffset < TOTAL_DAYS; dayOffset++) {
    // Calculate the target date (going backwards from today)
    const targetDate = new Date(today);
    targetDate.setDate(targetDate.getDate() - (TOTAL_DAYS - 1 - dayOffset));
    
    console.log(`\n${"=".repeat(80)}`);
    console.log(`DAY ${dayOffset + 1} - ${targetDate.toDateString()}`);
    console.log("=".repeat(80));
    
    // Create all promises for this day's questions
    const dayPromises: Promise<TestResult>[] = [];
    
    for (let questionIdx = 0; questionIdx < RUNS_PER_DAY; questionIdx++) {
      const question = questions[questionIdx % questions.length];
      const currentRunNumber = runNumber++;
      
      // Add some time variation within the day (spread across 12 hours)
      const targetDateTime = new Date(targetDate);
      targetDateTime.setHours(8); // Start at 8am
      targetDateTime.setMinutes(questionIdx * 72); // Spread across 12 hours (720 minutes / 10 = 72 minutes apart)
      
      // Create promise wrapped in semaphore for concurrency control
      const promise = semaphore.use(async () => {
        const result = await processQuestion(question, currentRunNumber, dayOffset, targetDateTime);
        completedRuns++;
        
        // Log progress
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        const rate = (completedRuns / (Date.now() - startTime) * 1000 * 60).toFixed(1);
        console.log(`  ✓ [${completedRuns}/${runsToComplete}] Run #${currentRunNumber} completed (${elapsed}s elapsed, ${rate} runs/min)`);
        
        return result;
      });
      
      dayPromises.push(promise);
    }
    
    // Wait for all questions in this day to complete
    const dayResults = await Promise.all(dayPromises);
    results.push(...dayResults);
    
    // Brief pause between days
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  const totalElapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1);
  console.log(`\n${"=".repeat(80)}`);
  console.log(`All inferences completed in ${totalElapsed} minutes`);
  console.log("=".repeat(80));

  // Generate summary
  console.log("\n" + "=".repeat(80));
  console.log("DEMO TEST RESULTS SUMMARY");
  console.log("=".repeat(80));
  
  const successful = results.filter(r => !r.error);
  const failed = results.filter(r => r.error);
  
  console.log(`\nTotal inferences in this run: ${results.length}`);
  console.log(`Successful: ${successful.length}`);
  console.log(`Failed: ${failed.length}`);
  console.log(`Days processed: ${START_FROM_DAY} to ${TOTAL_DAYS}`);
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
  
  for (let day = START_FROM_DAY; day <= TOTAL_DAYS; day++) {
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
  const dayRange = START_FROM_DAY === 1 ? "full" : `day${START_FROM_DAY}-${TOTAL_DAYS}`;
  const resultsPath = path.join(__dirname, `demo-results-${dayRange}-${timestamp}.json`);
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
