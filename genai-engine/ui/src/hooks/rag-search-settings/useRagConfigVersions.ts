import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type { ListRagSearchSettingConfigurationVersionsResponse } from "@/lib/api-client/api-client";

interface UseRagConfigVersionsParams {
  page?: number;
  page_size?: number;
  sort?: "asc" | "desc";
  tags?: string[];
  version_numbers?: number[];
}

export function useRagConfigVersions(configId: string | null, params?: UseRagConfigVersionsParams) {
  const api = useApi();

  return useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: ["rag-config-versions", configId, params],
    queryFn: async () => {
      if (!api || !configId) {
        throw new Error("API client or config ID not available");
      }

      const response = await api.api.getRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGet({
        settingConfigurationId: configId,
        ...params,
      });

      // Transform the response to normalize the key name
      const data: ListRagSearchSettingConfigurationVersionsResponse & { versions: typeof response.data.rag_provider_setting_configurations } = {
        ...response.data,
        versions: response.data.rag_provider_setting_configurations,
      };

      return data;
    },
    enabled: !!configId && !!api,
  });
}
