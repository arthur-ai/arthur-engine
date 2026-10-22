import { useAuth } from "@/contexts/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { GuardrailLLMConfiguration, ModelProvider } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useGuardrailPermissions = () => {
  const { me } = useAuth();
  const canWrite = me?.roles.includes("ORG-ADMIN") ?? false;
  return { canWrite, canRead: canWrite || (me?.roles.includes("ORG-AUDITOR") ?? false) };
};

export const useGuardrailConfiguration = () => {
  const { canRead } = useGuardrailPermissions();
  return useApiQuery({
    method: "getConfigurationApiV2ConfigurationGet",
    args: [],
    enabled: canRead,
    queryOptions: { queryKey: queryKeys.configuration.all(), retry: false },
  });
};

export const useGuardrailCatalog = (provider: ModelProvider | "", enabled: boolean) =>
  useApiQuery({
    method: "getModelProviderWhitelistApiV1ModelProvidersProviderModelWhitelistGet",
    args: [provider || "openai"],
    enabled: enabled && !!provider,
    queryOptions: { queryKey: queryKeys.providers.modelWhitelist(provider), retry: false },
  });

export const useSaveGuardrailConfiguration = () => {
  const api = useApi();
  const { canWrite } = useGuardrailPermissions();
  return useApiMutation({
    mutationFn: async (selection: GuardrailLLMConfiguration) => {
      if (!api || !canWrite) throw new Error("Guardrail settings cannot be changed.");
      const response = await api.api.updateConfigurationApiV2ConfigurationPost({ guardrail_llm: selection });
      return response.data;
    },
    invalidateQueries: [{ queryKey: queryKeys.configuration.all() }],
  });
};
