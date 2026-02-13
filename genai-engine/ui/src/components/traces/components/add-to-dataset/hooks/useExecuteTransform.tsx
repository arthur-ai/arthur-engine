import { useMutation } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { TransformExtractionResponseList } from "@/lib/api-client/api-client";

export const useExecuteTransform = (traceId: string, { onSuccess }: { onSuccess?: (data: TransformExtractionResponseList) => void }) => {
  const api = useApi()!;

  return useMutation({
    mutationFn: async ({ transformId }: { transformId: string }) => {
      const response = await api.api.executeTraceTransformExtractionApiV1TracesTraceIdTransformsTransformIdExtractionsPost(traceId, transformId);

      return response.data;
    },
    onSuccess,
  });
};
