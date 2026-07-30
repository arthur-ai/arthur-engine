import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProviderResponse, PutModelProviderCredentials } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useSaveProvider = () => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;

  return useMutation({
    mutationFn: async ({
      provider,
      data,
    }: {
      provider: ModelProviderResponse;
      data: PutModelProviderCredentials;
    }): Promise<ModelProviderResponse> => {
      const response = await api.setModelProviderApiV1ModelProvidersProviderPut(provider.provider, data);

      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers.all() });
    },
  });
};
