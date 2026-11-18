import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { useApiQuery } from "@/hooks/useApiQuery";
import { PutDefaultModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

// Saving or clearing the default changes what these reads show
const invalidateOnChange = [
  { queryKey: queryKeys.providers.default() },
  ...queryKeys.providers.defaultDependents().map((queryKey) => ({ queryKey })),
];

export const useDefaultModelProvider = () =>
  useApiQuery<"getDefaultModelProviderApiV1DefaultModelProviderGet">({
    method: "getDefaultModelProviderApiV1DefaultModelProviderGet",
    args: [] as const,
  });

export const useSetDefaultModelProvider = () => {
  const { api } = useApi()!;

  return useApiMutation({
    mutationFn: async (data: PutDefaultModelProvider) => {
      await api.setDefaultModelProviderApiV1DefaultModelProviderPut(data);
    },
    invalidateQueries: invalidateOnChange,
  });
};

export const useClearDefaultModelProvider = () => {
  const { api } = useApi()!;

  return useApiMutation({
    mutationFn: async () => {
      await api.clearDefaultModelProviderApiV1DefaultModelProviderDelete();
    },
    invalidateQueries: invalidateOnChange,
  });
};
