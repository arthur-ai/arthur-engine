import { useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useAuth } from "@/contexts/AuthContext";
import { queryKeys } from "@/lib/queryKeys";

import { useApi } from "@/hooks/useApi";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { ApplicationConfigurationUpdateRequest } from "@/lib/api-client/api-client";

const QUERY_METHOD = "getConfigurationApiV2ConfigurationGet" as const;

interface UseApplicationConfigurationOptions {
  enabled?: boolean;
}

export function useApplicationConfiguration(options: UseApplicationConfigurationOptions = {}) {
  const { enabled = true } = options;
  const { me } = useAuth();
  const canRead = me?.roles.some((role) => role === "ORG-ADMIN" || role === "ORG-AUDITOR") ?? false;
  const api = useApi();
  const queryClient = useQueryClient();

  const query = useApiQuery({
    method: QUERY_METHOD,
    args: [] as const,
    enabled: enabled && canRead,
    queryOptions: {
      retry: (failureCount, error) => {
        if (axios.isAxiosError(error) && error.response?.status === 403) return false;
        return failureCount < 1;
      },
    },
  });

  const updateConfiguration = async (body: ApplicationConfigurationUpdateRequest) => {
    if (!api) throw new Error("API client not available");
    const res = await api.api.updateConfigurationApiV2ConfigurationPost(body);
    await queryClient.invalidateQueries({
      queryKey: queryKeys.configuration.all(),
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
