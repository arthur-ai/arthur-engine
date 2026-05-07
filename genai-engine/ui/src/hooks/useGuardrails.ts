import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type { Api, NewRuleRequest, PromptValidationRequest, RuleResponse, TaskResponse, ValidationResult } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const taskRulesQueryOptions = ({ api, taskId }: { api: Api<unknown>; taskId: string }) =>
  queryOptions({
    queryKey: queryKeys.guardrails.rulesForTask(taskId),
    queryFn: async (): Promise<RuleResponse[]> => {
      const response = await api.api.getTaskApiV2TasksTaskIdGet(taskId);
      const task = response.data as TaskResponse;
      return task.rules ?? [];
    },
  });

export function useTaskRules(taskId: string) {
  const api = useApi();

  return useQuery({
    ...taskRulesQueryOptions({ api: api!, taskId }),
    enabled: !!api && !!taskId,
  });
}

export function useCreateRule(taskId: string) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation<RuleResponse, Error, NewRuleRequest>({
    mutationFn: async (rule) => {
      if (!api) throw new Error("API client not available");
      const response = await api.api.createTaskRuleApiV2TasksTaskIdRulesPost(taskId, rule);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.guardrails.rulesForTask(taskId) });
    },
  });
}

export function useArchiveRule(taskId: string) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (ruleId) => {
      if (!api) throw new Error("API client not available");
      await api.api.archiveTaskRuleApiV2TasksTaskIdRulesRuleIdDelete(taskId, ruleId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.guardrails.rulesForTask(taskId) });
    },
  });
}

export function useToggleRule(taskId: string) {
  const api = useApi();
  const queryClient = useQueryClient();

  return useMutation<void, Error, { ruleId: string; enabled: boolean }>({
    mutationFn: async ({ ruleId, enabled }) => {
      if (!api) throw new Error("API client not available");
      await api.api.updateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch(taskId, ruleId, { enabled });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.guardrails.rulesForTask(taskId) });
    },
  });
}

export function useValidatePrompt(taskId: string) {
  const api = useApi();

  return useMutation<ValidationResult, Error, PromptValidationRequest>({
    mutationFn: async (request) => {
      if (!api) throw new Error("API client not available");
      const response = await api.api.validatePromptEndpointApiV2TasksTaskIdValidatePromptPost(taskId, request);
      return response.data;
    },
  });
}
