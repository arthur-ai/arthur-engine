import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type {
  RagProviderConfigurationRequest,
  RagProviderConfigurationResponse,
  RagProviderConfigurationUpdateRequest,
  RagProviderTestConfigurationRequest,
  ConnectionCheckResult,
} from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export function useRagProviderMutations() {
  const api = useApi();
  const queryClient = useQueryClient();

  const createProvider = useMutation({
    mutationFn: async ({ taskId, data }: { taskId: string; data: RagProviderConfigurationRequest }): Promise<RagProviderConfigurationResponse> => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.createRagProviderApiV1TasksTaskIdRagProvidersPost(taskId, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      // Invalidate the providers list for the specific task
      queryClient.invalidateQueries({ queryKey: queryKeys.ragProviders.list(variables.taskId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.ragProviders.all() });
    },
  });

  const updateProvider = useMutation({
    mutationFn: async ({
      providerId,
      data,
    }: {
      providerId: string;
      data: RagProviderConfigurationUpdateRequest;
    }): Promise<RagProviderConfigurationResponse> => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.updateRagProviderApiV1RagProvidersProviderIdPatch(providerId, data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate all providers queries since we don't know which task this belongs to
      queryClient.invalidateQueries({ queryKey: queryKeys.ragProviders.all() });
    },
  });

  const deleteProvider = useMutation({
    mutationFn: async ({ providerId }: { providerId: string }) => {
      if (!api) {
        throw new Error("API client not available");
      }

      await api.api.deleteRagProviderApiV1RagProvidersProviderIdDelete(providerId);
    },
    onSuccess: () => {
      // Invalidate all providers and collections queries
      queryClient.invalidateQueries({ queryKey: queryKeys.ragProviders.all() });
      queryClient.invalidateQueries({ queryKey: queryKeys.ragCollections.all() });
    },
  });

  const testConnection = useMutation({
    mutationFn: async ({ taskId, data }: { taskId: string; data: RagProviderTestConfigurationRequest }): Promise<ConnectionCheckResult> => {
      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.testRagProviderConnectionApiV1TasksTaskIdRagProvidersTestConnectionPost(taskId, data);
      return response.data;
    },
  });

  return {
    createProvider,
    updateProvider,
    deleteProvider,
    testConnection,
  };
}
