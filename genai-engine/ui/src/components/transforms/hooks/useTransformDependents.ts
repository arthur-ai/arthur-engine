import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { TransformDependents } from "@/lib/api-client/api-client";

const EMPTY_DEPENDENTS: TransformDependents = {
  continuous_evals: [],
  agentic_experiments: [],
  agentic_notebooks: [],
};

export function useTransformDependents(transformId: string | null) {
  const api = useApi();

  const query = useQuery({
    queryKey: ["transformDependents", transformId, api],
    queryFn: async () => {
      if (!api) throw new Error("API not available");

      const response = await api.api.getTransformDependentsApiV1TracesTransformsTransformIdDependentsGet(transformId!);
      return response.data;
    },
    enabled: !!transformId && !!api,
  });

  return {
    dependents: query.data ?? EMPTY_DEPENDENTS,
    isLoading: query.isLoading && !!transformId,
    error: query.error,
  };
}
