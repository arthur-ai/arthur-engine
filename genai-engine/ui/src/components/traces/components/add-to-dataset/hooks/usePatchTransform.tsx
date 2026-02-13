import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Column } from "../form/shared";
import { buildTransformFromColumns } from "../utils/transformBuilder";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { TraceTransformResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const usePatchTransform = (columns: Column[], { onSuccess }: { onSuccess?: (data: TraceTransformResponse) => void }) => {
  const queryClient = useQueryClient();
  const api = useApi()!;
  const { task } = useTask()!;

  const transformDef = buildTransformFromColumns(columns);

  return useMutation({
    mutationFn: async (transformId: string) => {
      const response = await api.api.updateTransformApiV1TracesTransformsTransformIdPatch(transformId, {
        definition: transformDef,
      });

      return response.data;
    },
    onSuccess: (data, transformId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transforms.list(task!.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.transforms.byId(transformId) });

      onSuccess?.(data);
    },
  });
};
