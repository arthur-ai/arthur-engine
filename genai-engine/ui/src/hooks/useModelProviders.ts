import { useQuery } from "@tanstack/react-query";

import { useApi } from "./useApi";
import { useApiQuery } from "./useApiQuery";

import type { ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

/**
 * Hook to fetch enabled model providers using TanStack Query.
 */
export function useModelProviders() {
  const { data, error, isLoading } = useApiQuery<"getModelProvidersApiV1ModelProvidersGet">({
    method: "getModelProvidersApiV1ModelProvidersGet",
    args: [] as const,
    queryOptions: {
      staleTime: 60000,
      refetchOnWindowFocus: false,
    },
  });

  const enabledProviders: ModelProvider[] =
    data?.providers?.filter((provider: ModelProviderResponse) => provider.enabled).map((provider: ModelProviderResponse) => provider.provider) ?? [];

  return {
    providers: enabledProviders,
    error,
    isLoading,
  };
}

/**
 * Hook to fetch available models for all enabled providers.
 * Automatically refetches when the provider list changes.
 */
export function useAvailableModels(enabledProviders: ModelProvider[]) {
  const api = useApi();

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  const { data, error, isLoading, refetch } = useQuery<{ models: Map<ModelProvider, string[]>; failed: ModelProvider[] }>({
    queryKey: queryKeys.providers.availableModels(enabledProviders),
    queryFn: async () => {
      if (!api) throw new Error("API client not initialized");

      const results = await Promise.all(
        enabledProviders.map(async (provider) => {
          try {
            const response = await api.api.getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet(provider);
            return { provider, models: response.data.available_models, failed: false };
          } catch (error) {
            console.error(`Failed to fetch models for provider ${provider}:`, error);
            return { provider, models: [] as string[], failed: true };
          }
        })
      );

      const modelsMap = new Map<ModelProvider, string[]>();
      results.forEach(({ provider, models }) => {
        modelsMap.set(provider, models);
      });
      return { models: modelsMap, failed: results.filter((r) => r.failed).map((r) => r.provider) };
    },
    enabled: !!api && enabledProviders.length > 0,
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });

  return {
    availableModels: data?.models ?? new Map<ModelProvider, string[]>(),
    /** Providers whose model list failed to load, as opposed to loading empty. */
    failedProviders: data?.failed ?? [],
    refetchAvailableModels: refetch,
    error,
    isLoading,
  };
}
