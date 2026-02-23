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

  const { data, error, isLoading } = useQuery<Map<ModelProvider, string[]>>({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.providers.availableModels(enabledProviders),
    queryFn: async () => {
      if (!api) throw new Error("API client not initialized");

      const results = await Promise.all(
        enabledProviders.map(async (provider) => {
          try {
            const response = await api.api.getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet(provider);
            return { provider, models: response.data.available_models };
          } catch (error) {
            console.error(`Failed to fetch models for provider ${provider}:`, error);
            return { provider, models: [] as string[] };
          }
        })
      );

      const modelsMap = new Map<ModelProvider, string[]>();
      results.forEach(({ provider, models }) => {
        modelsMap.set(provider, models);
      });
      return modelsMap;
    },
    enabled: !!api && enabledProviders.length > 0,
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });

  return {
    availableModels: data ?? new Map<ModelProvider, string[]>(),
    error,
    isLoading,
  };
}
