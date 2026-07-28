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
      // availableModels is keyed by the provider list, not a single provider, and
      // useAvailableModels holds it for 60s. Without this the AI Assistant picker
      // keeps showing the pre-save list for up to a minute.
      await queryClient.invalidateQueries({ queryKey: ["availableModels"] });
    },
  });
};
