import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";

type Opts = {
  onSuccess?: () => Promise<void>;
};

export const useRemoveProvider = ({ onSuccess }: Opts = {}) => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;

  return useMutation({
    mutationFn: async (provider: ModelProvider) => {
      const response = await api.deleteModelProviderApiV1ModelProvidersProviderDelete(provider);

      return response.data;
    },
    onSuccess: async (_data, provider) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers.all() });

      track(EVENT_NAMES.MODEL_PROVIDER_DELETED, { provider_name: provider });

      await onSuccess?.();
    },
    onError: (_error, provider) => {
      track(EVENT_NAMES.MODEL_PROVIDER_DELETE_FAILED, { provider_name: provider });
    },
  });
};
