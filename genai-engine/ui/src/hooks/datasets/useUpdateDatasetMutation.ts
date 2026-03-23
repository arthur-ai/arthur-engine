import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import type { NewDatasetRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";

export interface UseUpdateDatasetMutationReturn {
  mutateAsync: (data: NewDatasetRequest & { id: string }) => Promise<void>;
  isPending: boolean;
}

export function useUpdateDatasetMutation(onSuccess: () => void): UseUpdateDatasetMutationReturn {
  const api = useApi();

  const { mutateAsync, isPending } = useApiMutation({
    mutationFn: async (data: NewDatasetRequest & { id: string }) => {
      if (!api) throw new Error("API not available");

      return api.api.updateDatasetApiV2DatasetsDatasetIdPatch(data.id, {
        name: data.name,
        description: data.description || null,
        metadata: data.metadata || null,
      });
    },
    invalidateQueries: [{ queryKey: queryKeys.datasets.search.all() }],
    onSuccess: (_, data) => {
      track(EVENT_NAMES.DATASET_UPDATED, { dataset_id: data.id });
      onSuccess();
    },
    onError: (err) => {
      console.error("Failed to update dataset:", err);
    },
  });

  return {
    mutateAsync: async (data: NewDatasetRequest & { id: string }) => {
      await mutateAsync(data);
    },
    isPending,
  };
}
