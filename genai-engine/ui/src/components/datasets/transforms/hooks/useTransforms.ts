import { useQuery } from "@tanstack/react-query";
import { useApi } from "@/hooks/useApi";
import { DatasetTransform } from "../types";

// Fetches transforms for a dataset, returns empty array if none exist
export function useTransforms(datasetId: string | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: ["transforms", datasetId],
    queryFn: async () => {
      if (!datasetId || !api) return [];

      try {
        const response = await api.api.listTransformsApiV2DatasetsDatasetIdTransformsGet(datasetId);
        return (response.data.transforms || []) as DatasetTransform[];
      } catch (error: any) {
        if (error.response?.status === 404) return [];
        throw error;
      }
    },
    enabled: !!datasetId && !!api,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
