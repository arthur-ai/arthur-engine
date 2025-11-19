import { useQuery, UseQueryResult } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type { RagProviderCollectionResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

interface UseRagCollectionsResult {
  collections: RagProviderCollectionResponse[];
  count: number;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

interface RagCollectionsResponse {
  rag_provider_collections: RagProviderCollectionResponse[];
  count: number;
}

export function useRagCollections(providerId: string | undefined): UseRagCollectionsResult {
  const api = useApi();

  const queryResult: UseQueryResult<RagCollectionsResponse, Error> = useQuery<RagCollectionsResponse, Error>({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.ragCollections.list(providerId || ""),
    queryFn: async () => {
      if (!providerId || !api) {
        throw new Error("Provider ID or API not available");
      }

      const response = await api.api.listRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGet(providerId);

      return response.data;
    },
    enabled: !!providerId && !!api,
  });

  return {
    collections: queryResult.data?.rag_provider_collections || [],
    count: queryResult.data?.count || 0,
    isLoading: queryResult.isLoading,
    error: queryResult.error,
    refetch: queryResult.refetch,
  };
}
