import { useApiQuery } from "@/hooks/useApiQuery";
import type { ModelProvider, ModelReasoningOptions } from "@/lib/api-client/api-client";

/**
 * The reasoning settings litellm accepts for a model, as the backend checks them
 * when an eval is saved. Undefined until a provider and model are chosen and the
 * request returns.
 */
export const useModelReasoningOptions = (provider: ModelProvider | "", modelName: string): ModelReasoningOptions | undefined => {
  const { data } = useApiQuery({
    method: "getModelReasoningOptionsApiV1ModelProvidersProviderReasoningOptionsGet",
    args: [{ provider: provider as ModelProvider, model_name: modelName }],
    enabled: provider !== "" && modelName !== "",
    queryOptions: { staleTime: Infinity },
  });
  return provider !== "" && modelName !== "" ? data : undefined;
};
