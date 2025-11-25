import { AISpanType, TracingContext } from "@mastra/core/ai-tracing";
import type { MessageInput } from "@mastra/core/agent/message-list";
import { getArthurApiClient } from "./client";

export interface PromptVariable {
  name: string;
  value: string;
}

export interface GetTemplatedPromptOptions {
  /** The name of the prompt in Arthur */
  promptName: string;
  /** The version tag or number of the prompt */
  promptVersion: string;
  /** The Arthur task ID */
  taskId: string;
  /** Variables to template into the prompt - can be an object or array of PromptVariable */
  variables: Record<string, any> | PromptVariable[];
  /** Optional tracing context for creating spans */
  tracingContext?: TracingContext;
}

export interface TemplatedPromptResult {
  /** The name of the agentic prompt */
  name: string;
  /** The rendered messages ready for agent consumption */
  messages: MessageInput[];
  /** Name of the LLM model */
  model_name: string;
  /** Provider of the LLM model */
  model_provider: string;
  /** Version of the agentic prompt */
  version: number;
  /** Available tools/functions for the model to call */
  tools?: any[];
  /** List of variable names for the agentic prompt */
  variables: string[];
  /** List of tags for this agentic prompt version */
  tags: string[];
  /** LLM configurations for this prompt */
  config?: any;
  /** Timestamp when the prompt was created */
  created_at: string;
  /** Time that this prompt was deleted (if applicable) */
  deleted_at?: string | null;
}

/**
 * Retrieves a templated prompt from Arthur GenAI Engine with tracing support
 *
 * @param options - Configuration for retrieving and templating the prompt
 * @returns The complete agentic prompt object including rendered messages and metadata
 *
 * @example
 * ```typescript
 * // Using an object (recommended)
 * const result = await getTemplatedPrompt({
 *   promptName: "text-to-sql",
 *   promptVersion: "production",
 *   taskId: process.env.ARTHUR_TASK_ID!,
 *   variables: {
 *     database: "postgres",
 *     query: "Show me all users",
 *     schema: { tables: ["users", "orders"] }
 *   },
 *   tracingContext
 * });
 *
 * // Access the rendered messages
 * console.log(result.messages);
 *
 * // Access prompt metadata
 * console.log(result.model_name); // e.g., "gpt-4"
 * console.log(result.version); // e.g., 1
 * console.log(result.config); // LLM configuration
 *
 * // Or using an array of PromptVariable
 * const result = await getTemplatedPrompt({
 *   promptName: "text-to-sql",
 *   promptVersion: "production",
 *   taskId: process.env.ARTHUR_TASK_ID!,
 *   variables: [
 *     { name: "database", value: "postgres" },
 *     { name: "query", value: "Show me all users" }
 *   ],
 *   tracingContext
 * });
 * ```
 */
export async function getTemplatedPrompt(
  options: GetTemplatedPromptOptions
): Promise<TemplatedPromptResult> {
  const { promptName, promptVersion, taskId, variables, tracingContext } =
    options;

  // Convert variables object to PromptVariable array if needed
  const promptVariables: PromptVariable[] = Array.isArray(variables)
    ? variables
    : Object.entries(variables).map(([name, value]) => ({
        name,
        value:
          value === undefined
            ? ""
            : typeof value === "object"
            ? JSON.stringify(value)
            : typeof value === "string"
            ? value
            : String(value),
      }));

  // Create a span for prompt templating if tracing context is provided
  const promptSpan = tracingContext?.currentSpan?.createChildSpan({
    type: AISpanType.GENERIC,
    name: `template prompt: ${promptName}`,
    input: {
      promptName,
      promptVersion,
      taskId,
      variables: promptVariables.reduce(
        (acc, v) => ({ ...acc, [v.name]: v.value }),
        {}
      ),
    },
    metadata: {
      type: "prompt_templating",
      source: "arthur",
    },
  });

  try {
    const api = getArthurApiClient();

    const response =
      await api.api.renderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPost(
        promptName,
        promptVersion,
        taskId,
        {
          completion_request: {
            strict: true,
            variables: promptVariables,
          },
        }
      );

    // Extract the full agentic prompt response
    const agenticPrompt = response.data as TemplatedPromptResult;

    // Cast the messages to the expected format for Mastra agent
    const messages = agenticPrompt.messages as MessageInput[];

    // End the span with success
    promptSpan?.end({
      output: {
        promptName: agenticPrompt.name,
        promptVersion: agenticPrompt.version,
        modelName: agenticPrompt.model_name,
        modelProvider: agenticPrompt.model_provider,
        messagesCount: messages.length,
        messages,
      },
      metadata: {
        success: true,
      },
    });

    return {
      ...agenticPrompt,
      messages,
    };
  } catch (error) {
    // End the span with error
    promptSpan?.end({
      output: {
        error: error instanceof Error ? error.message : String(error),
      },
      metadata: {
        success: false,
      },
    });

    throw error;
  }
}
