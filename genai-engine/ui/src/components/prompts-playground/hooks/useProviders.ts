import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useProviders = () => {
  const api = useApi()!;

  return useQuery({
    queryKey: queryKeys.providers.all(),
    queryFn: async () => {
      const response = await api.api.getModelProvidersApiV1ModelProvidersGet();
      return response.data.providers;
    },
  });
};

export const useAvailableModels = (provider?: ModelProvider) => {
  const api = useApi()!;

  return useQuery({
    queryKey: queryKeys.providers.availableModels(provider!),
    queryFn: async () => {
      const response = await api.api.getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet(provider!);
      return response.data.available_models;
    },
    enabled: !!provider,
  });
};
