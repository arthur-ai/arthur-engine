import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useModelWhitelist = (provider: ModelProvider, enabled: boolean) => {
  const api = useApi();

  return useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.providers.modelWhitelist(provider),
    queryFn: async () => {
      if (!api) throw new Error("API client not initialized");
      const response = await api.api.getModelProviderWhitelistApiV1ModelProvidersProviderModelWhitelistGet(provider);
      return response.data;
    },
    enabled: !!api && enabled,
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });
};
