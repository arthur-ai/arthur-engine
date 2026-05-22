import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { TraceTransformVersionResponse } from "@/lib/api-client/api-client";

export type { TraceTransformVersionResponse };

export function useTransformVersions(transformId: string | null | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["transformVersions", transformId, api],
    queryFn: async (): Promise<TraceTransformVersionResponse[]> => {
      if (!transformId || !api) return [];

      try {
        const response = await api.api.listTransformVersionsApiV1TracesTransformsTransformIdVersionsGet(transformId);
        return response.data.versions || [];
      } catch (error: unknown) {
        if (error && typeof error === "object" && "response" in error) {
          const apiError = error as { response?: { status?: number } };
          if (apiError.response?.status === 404) return [];
        }
        throw error;
      }
    },
    enabled: !!transformId && !!api,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}
