import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { PutDefaultModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useDefaultModelProvider = () => {
  const api = useApi()!;

  return useQuery({
    queryKey: queryKeys.providers.default(),
    queryFn: async () => {
      const response = await api.api.getDefaultModelProviderApiV1DefaultModelProviderGet();
      return response.data;
    },
  });
};

export const useSetDefaultModelProvider = () => {
  const { api } = useApi()!;

  return useApiMutation({
    mutationFn: async (data: PutDefaultModelProvider) => {
      await api.setDefaultModelProviderApiV1DefaultModelProviderPut(data);
    },
    invalidateQueries: [{ queryKey: queryKeys.providers.default() }],
  });
};

export const useClearDefaultModelProvider = () => {
  const { api } = useApi()!;

  return useApiMutation({
    mutationFn: async () => {
      await api.clearDefaultModelProviderApiV1DefaultModelProviderDelete();
    },
    invalidateQueries: [{ queryKey: queryKeys.providers.default() }],
  });
};
