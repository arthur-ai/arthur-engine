import { PromptType, PromptPlaygroundState } from "../types";
import { toExperimentPromptConfig } from "./toExperimentPromptConfig";
import toFrontendPrompt from "./toFrontendPrompt";
import { NotebookStateInput, NotebookStateOutput, SavedPromptConfig, UnsavedPromptConfig } from "@/lib/api-client/api-client";

/**
 * Serializes the current playground state to NotebookStateInput format
 * For Iteration Mode, this only includes prompts
 * For Experiment Mode, includes prompts + dataset + evals + mappings
 */
export const serializePlaygroundState = (
  state: PromptPlaygroundState,
  experimentConfig?: any
): NotebookStateInput => {
  // Convert prompts to experiment prompt configs
  const prompt_configs = state.prompts.map((prompt) => toExperimentPromptConfig(prompt));

  // If experimentConfig is provided, include it in the serialized state (Experiment Mode)
  if (experimentConfig && experimentConfig.dataset_ref) {
    return {
      prompt_configs: prompt_configs.length > 0 ? prompt_configs : null,
      prompt_variable_mapping: experimentConfig.prompt_variable_mapping || null,
      dataset_ref: experimentConfig.dataset_ref,
      eval_list: experimentConfig.eval_list || null,
      dataset_row_filter: experimentConfig.dataset_row_filter || null,
    };
  }

  // Iteration Mode - only prompts
  return {
    prompt_configs: prompt_configs.length > 0 ? prompt_configs : null,
    prompt_variable_mapping: null,
    dataset_ref: null,
    eval_list: null,
    dataset_row_filter: null,
  };
};

/**
 * Deserializes NotebookStateOutput to playground prompts and full state
 * Returns prompts, keywords, and the complete notebook state for experiment mode detection
 */
export const deserializeNotebookState = async (
  notebookState: NotebookStateOutput,
  apiClient: any,
  taskId: string
): Promise<{
  prompts: PromptType[];
  keywords: Map<string, string>;
  fullState: NotebookStateOutput;
}> => {
  const prompts: PromptType[] = [];
  const keywords = new Map<string, string>();

  // Process prompt configs
  if (notebookState.prompt_configs && notebookState.prompt_configs.length > 0) {
    for (const promptConfig of notebookState.prompt_configs) {
      if (promptConfig.type === "saved") {
        // Fetch saved prompt from backend
        const savedConfig = promptConfig as { type: "saved" } & SavedPromptConfig;
        try {
          const response = await apiClient.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
            savedConfig.name,
            savedConfig.version.toString(),
            taskId
          );
          const frontendPrompt = toFrontendPrompt(response.data);
          prompts.push(frontendPrompt);
        } catch (error) {
          console.error(`Failed to fetch saved prompt ${savedConfig.name} v${savedConfig.version}:`, error);
        }
      } else if (promptConfig.type === "unsaved") {
        // Convert unsaved prompt config to frontend format
        const unsavedConfig = promptConfig as { type: "unsaved" } & UnsavedPromptConfig;

        // Create a frontend prompt from the unsaved config
        const frontendPrompt: PromptType = {
          id: unsavedConfig.auto_name || `unsaved-${Date.now()}`,
          classification: "default",
          name: unsavedConfig.auto_name || "",
          created_at: undefined,
          modelName: unsavedConfig.model_name || "",
          modelProvider: unsavedConfig.model_provider || "",
          messages: unsavedConfig.messages?.map((msg, idx) => ({
            id: `msg-${idx}`,
            role: msg.role,
            content: msg.content || "",
            disabled: false,
            ...(msg.tool_calls ? { tool_calls: msg.tool_calls } : {}),
          })) || [],
          modelParameters: {
            temperature: unsavedConfig.config?.temperature ?? null,
            top_p: unsavedConfig.config?.top_p ?? null,
            timeout: unsavedConfig.config?.timeout ?? null,
            stream: unsavedConfig.config?.stream ?? true,
            stream_options: unsavedConfig.config?.stream_options ?? null,
            max_tokens: unsavedConfig.config?.max_tokens ?? null,
            max_completion_tokens: unsavedConfig.config?.max_completion_tokens ?? null,
            frequency_penalty: unsavedConfig.config?.frequency_penalty ?? null,
            presence_penalty: unsavedConfig.config?.presence_penalty ?? null,
            stop: unsavedConfig.config?.stop ?? null,
            seed: unsavedConfig.config?.seed ?? null,
            reasoning_effort: unsavedConfig.config?.reasoning_effort ?? null,
            logprobs: unsavedConfig.config?.logprobs ?? null,
            top_logprobs: unsavedConfig.config?.top_logprobs ?? null,
            logit_bias: unsavedConfig.config?.logit_bias ?? null,
            thinking: unsavedConfig.config?.thinking ?? null,
          },
          runResponse: null,
          responseFormat: unsavedConfig.config?.response_format,
          tools: unsavedConfig.tools?.map((tool, idx) => ({
            id: `tool-${idx}`,
            type: tool.type,
            function: tool.function,
            strict: tool.strict ?? false,
          })) || [],
          toolChoice: unsavedConfig.config?.tool_choice,
          running: false,
          version: null,
          isDirty: false,
        };

        prompts.push(frontendPrompt);
      }
    }
  }

  // Process variable mappings to restore keyword values
  if (notebookState.prompt_variable_mapping && notebookState.prompt_variable_mapping.length > 0) {
    notebookState.prompt_variable_mapping.forEach((mapping) => {
      // Initialize with empty values - will be populated by dataset or user input
      keywords.set(mapping.variable_name, "");
    });
  }

  return { prompts, keywords, fullState: notebookState };
};
