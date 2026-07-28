import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

/**
 * Reads a provider's curated model list plus its full catalog. The catalog comes
 * back alongside the selection so the editor can offer models the admin removed.
 *
 * Only meaningful for a configured provider — the endpoint 400s otherwise, which
 * is why callers gate this with `enabled`.
 */
export const useModelWhitelist = (provider: ModelProvider, enabled: boolean) => {
  const api = useApi();

  return useQuery({
    // The api client is not serialisable and its identity carries no cache meaning;
    // the provider alone identifies this query. Same treatment as useAvailableModels.
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
