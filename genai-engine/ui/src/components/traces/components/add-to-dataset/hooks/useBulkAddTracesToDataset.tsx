import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { BulkAddTracesToDatasetResponse } from "@/lib/api-client/api-client";

type BulkAddTracesVariables = {
  datasetId: string;
  transformId: string;
  traceIds: string[];
};

export const useBulkAddTracesToDataset = ({
  onSuccess,
  onError,
}: {
  onSuccess?: (data: BulkAddTracesToDatasetResponse, variables: BulkAddTracesVariables) => void;
  onError?: (error: Error, variables: BulkAddTracesVariables) => void;
} = {}) => {
  const api = useApi()!;

  return useApiMutation<BulkAddTracesToDatasetResponse, BulkAddTracesVariables>({
    mutationFn: async ({ datasetId, transformId, traceIds }) => {
      const response = await api.api.bulkAddTracesToDatasetApiV2DatasetsDatasetIdBulkAddTracesPost(datasetId, {
        transform_id: transformId,
        trace_ids: traceIds,
      });

      return response.data;
    },
    onSuccess,
    onError,
  });
};
