import { useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { ApplicationConfigurationUpdateRequest } from "@/lib/api-client/api-client";

const QUERY_METHOD = "getConfigurationApiV2ConfigurationGet" as const;

export function useApplicationConfiguration() {
  const api = useApi();
  const queryClient = useQueryClient();

  const query = useApiQuery({
    method: QUERY_METHOD,
    args: [] as const,
  });

  const updateConfiguration = async (body: ApplicationConfigurationUpdateRequest) => {
    if (!api) throw new Error("API client not available");
    const res = await api.api.updateConfigurationApiV2ConfigurationPost(body);
    await queryClient.invalidateQueries({
      queryKey: [QUERY_METHOD],
    });
    return res.data;
  };

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    updateConfiguration,
  };
}
