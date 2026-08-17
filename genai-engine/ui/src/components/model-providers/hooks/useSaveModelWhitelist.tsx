import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { ModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useSaveModelWhitelist = () => {
  const queryClient = useQueryClient();
  const { api } = useApi()!;

  return useMutation({
    mutationFn: async ({ provider, models }: { provider: ModelProvider; models: string[] | null }) => {
      await api.setModelProviderWhitelistApiV1ModelProvidersProviderModelWhitelistPut(provider, { models });
    },
    onSuccess: async (_data, { provider }) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers.modelWhitelist(provider) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers.availableModelsAll() });
    },
  });
};
