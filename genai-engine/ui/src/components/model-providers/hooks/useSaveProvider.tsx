import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProviderResponse, PutModelProviderCredentials } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";

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
    onSuccess: async (data, variables) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers.all() });

      track(EVENT_NAMES.MODEL_PROVIDER_SAVED, { provider_name: data.provider });

      if (data.enabled !== variables.provider.enabled) {
        track(EVENT_NAMES.MODEL_PROVIDER_STATUS_CHANGED, { provider_name: data.provider });
      }

      await onSuccess?.(data);
    },
    onError: (_error, variables) => {
      track(EVENT_NAMES.MODEL_PROVIDER_SAVE_FAILED, { provider_name: variables.provider.provider });
    },
  });
};
