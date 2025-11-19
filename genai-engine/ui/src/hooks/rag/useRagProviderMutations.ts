import { useMutation, useQueryClient, UseMutationResult } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type {
  RagProviderConfigurationRequest,
  RagProviderConfigurationResponse,
  RagProviderConfigurationUpdateRequest,
  RagProviderTestConfigurationRequest,
  ConnectionCheckResult,
} from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

interface CreateProviderVariables {
  taskId: string;
  data: RagProviderConfigurationRequest;
}

interface UpdateProviderVariables {
  providerId: string;
  data: RagProviderConfigurationUpdateRequest;
}

interface DeleteProviderVariables {
  providerId: string;
}

interface TestConnectionVariables {
  taskId: string;
  data: RagProviderTestConfigurationRequest;
}

interface UseRagProviderMutationsResult {
  createProvider: UseMutationResult<RagProviderConfigurationResponse, Error, CreateProviderVariables>;
  updateProvider: UseMutationResult<RagProviderConfigurationResponse, Error, UpdateProviderVariables>;
  deleteProvider: UseMutationResult<void, Error, DeleteProviderVariables>;
  testConnection: UseMutationResult<ConnectionCheckResult, Error, TestConnectionVariables>;
}

export function useRagProviderMutations(): UseRagProviderMutationsResult {
  const api = useApi();
  const queryClient = useQueryClient();

  const createProvider = useMutation<RagProviderConfigurationResponse, Error, CreateProviderVariables>({
    mutationFn: async ({ taskId, data }) => {
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

  const updateProvider = useMutation<RagProviderConfigurationResponse, Error, UpdateProviderVariables>({
    mutationFn: async ({ providerId, data }) => {
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

  const deleteProvider = useMutation<void, Error, DeleteProviderVariables>({
    mutationFn: async ({ providerId }) => {
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

  const testConnection = useMutation<ConnectionCheckResult, Error, TestConnectionVariables>({
    mutationFn: async ({ taskId, data }) => {
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
