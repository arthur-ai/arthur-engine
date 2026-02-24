import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ContentType } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export interface ApplicationConfigurationResponse {
  chat_task_id?: string | null;
  document_storage_configuration?: unknown;
  max_llm_rules_per_task_count: number;
  trace_retention_days: number;
}

export interface ApplicationConfigurationUpdateRequest {
  trace_retention_days?: number | null;
}

const CONFIG_PATH = "/api/v2/configuration";

export function useApplicationConfiguration() {
  const api = useApi();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: [...queryKeys.applicationConfiguration(), api],
    queryFn: async (): Promise<ApplicationConfigurationResponse> => {
      if (!api) throw new Error("API client not available");
      const res = await api.request<ApplicationConfigurationResponse>({
        method: "GET",
        path: CONFIG_PATH,
        secure: true,
      });
      return res.data;
    },
    enabled: !!api,
  });

  const updateConfiguration = async (body: ApplicationConfigurationUpdateRequest): Promise<ApplicationConfigurationResponse> => {
    if (!api) throw new Error("API client not available");
    const res = await api.request<ApplicationConfigurationResponse>({
      method: "POST",
      path: CONFIG_PATH,
      secure: true,
      type: ContentType.Json,
      body,
    });
    await queryClient.invalidateQueries({ queryKey: queryKeys.applicationConfiguration() });
    return res.data;
  };

  const { data, isLoading, isPending, error, refetch } = query;
  return { data, isLoading, isPending, error, refetch, updateConfiguration };
}
