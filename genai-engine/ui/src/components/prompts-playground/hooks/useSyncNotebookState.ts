import { useQuery } from "@tanstack/react-query";
import { useEffect, useEffectEvent } from "react";

import { PromptType } from "../types";
import { toFrontendPrompt } from "../utils";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { NotebookStateOutput, SavedPromptConfig, UnsavedPromptConfig } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Props = {
  enabled: boolean;
  notebookId: string;
  onSuccess: (data: { prompts: PromptType[]; keywords: Map<string, string>; fullState: NotebookStateOutput }) => void;
};

export const useSyncNotebookState = ({ enabled, notebookId, onSuccess }: Props) => {
  const api = useApi();
  const { task } = useTask();

  const notebookStateQuery = useQuery({
    queryKey: queryKeys.notebooks.state.get(notebookId!),
    queryFn: () => api?.api.getNotebookStateApiV1NotebooksNotebookIdStateGet(notebookId!),
    enabled,
    select: (data) => data?.data,
    refetchOnWindowFocus: false,
  });

  const deserializedNotebookState = useQuery({
    queryKey: queryKeys.notebooks.state.deserialize(notebookStateQuery.data!),
    queryFn: async () => {
      const state = notebookStateQuery.data!;

      const configs: { saved: SavedPromptConfig[]; unsaved: UnsavedPromptConfig[] } = {
        saved: [],
        unsaved: [],
      };

      for (const promptConfig of state?.prompt_configs || []) {
        if (promptConfig.type === "saved") {
          configs.saved.push(promptConfig);
        } else {
          configs.unsaved.push(promptConfig);
        }
      }

      const promises = configs.saved
        .map((prompt) => {
          return api?.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(prompt.name, prompt.version.toString(), task!.id);
        })
        .filter(Boolean);

      // Initialize prompts with saved prompts
      const prompts = await Promise.all(promises)
        .then((responses) => responses.map((response) => response?.data).filter(Boolean))
        .then((prompts) => prompts.map((prompt) => toFrontendPrompt(prompt)));

      // Add unsaved prompts
      for (const promptConfig of configs.unsaved) {
        prompts.push(createUnsavedPrompt(promptConfig));
      }

      const keywords = new Map<string, string>();
      for (const promptConfig of state?.prompt_variable_mapping || []) {
        keywords.set(promptConfig.variable_name, "");
      }

      return {
        prompts,
        keywords,
        fullState: state,
      };
    },
    enabled: !!notebookStateQuery.data,
    refetchOnWindowFocus: false,
  });

  const handleSyncNotebookState = useEffectEvent((data: typeof deserializedNotebookState.data) => {
    if (!data) {
      return;
    }

    onSuccess(data);
  });

  useEffect(() => {
    if (!deserializedNotebookState.data) return;

    handleSyncNotebookState(deserializedNotebookState.data);
  }, [deserializedNotebookState.data]);

  return {
    loading: notebookStateQuery.isLoading || deserializedNotebookState.isLoading,
  };
};

const createUnsavedPrompt = (config: UnsavedPromptConfig): PromptType => {
  return {
    id: config.auto_name || `unsaved-${Date.now()}`,
    classification: "default",
    name: config.auto_name || "",
    created_at: undefined,
    modelName: config.model_name || "",
    modelProvider: config.model_provider || "",
    messages:
      config.messages?.map((msg, idx) => ({
        id: `msg-${idx}`,
        role: msg.role,
        content: msg.content || "",
        disabled: false,
        ...(msg.tool_calls ? { tool_calls: msg.tool_calls } : {}),
      })) || [],
    modelParameters: {
      temperature: config.config?.temperature ?? null,
      top_p: config.config?.top_p ?? null,
      timeout: config.config?.timeout ?? null,
      stream: config.config?.stream ?? true,
      stream_options: config.config?.stream_options ?? null,
      max_tokens: config.config?.max_tokens ?? null,
      max_completion_tokens: config.config?.max_completion_tokens ?? null,
      frequency_penalty: config.config?.frequency_penalty ?? null,
      presence_penalty: config.config?.presence_penalty ?? null,
      stop: config.config?.stop ?? null,
      seed: config.config?.seed ?? null,
      reasoning_effort: config.config?.reasoning_effort ?? null,
      logprobs: config.config?.logprobs ?? null,
      top_logprobs: config.config?.top_logprobs ?? null,
      logit_bias: config.config?.logit_bias ?? null,
      thinking: config.config?.thinking ?? null,
    },
    runResponse: null,
    responseFormat: config.config?.response_format,
    tools:
      config.tools?.map((tool, idx) => ({
        id: `tool-${idx}`,
        type: tool.type,
        function: tool.function,
        strict: tool.strict ?? false,
      })) || [],
    toolChoice: config.config?.tool_choice,
    running: false,
    version: null,
    isDirty: false,
  };
};
