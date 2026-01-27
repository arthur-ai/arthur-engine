import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProviderResponse, PutModelProviderCredentials } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Opts = {
  onSuccess?: (data: ModelProviderResponse) => Promise<void>;
};

export const useSaveProvider = ({ onSuccess }: Opts = {}) => {
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
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers.all() });

      await onSuccess?.(data);
    },
  });
};
