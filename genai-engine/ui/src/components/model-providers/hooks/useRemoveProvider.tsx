import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

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
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers.all() });

      await onSuccess?.();
    },
  });
};
