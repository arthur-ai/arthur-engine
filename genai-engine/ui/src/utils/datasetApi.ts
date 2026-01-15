import { MAX_DATASET_ROWS } from "@/constants/datasetConstants";
import type { Api, DatasetVersionRowResponse } from "@/lib/api-client/api-client";

/**
 * Fetches all rows from a dataset version in a single request.
 */
export async function fetchAllDatasetRows(api: Api<unknown>, datasetId: string, versionNumber: number): Promise<DatasetVersionRowResponse[]> {
  const response = await api.api.getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet({
    datasetId,
    versionNumber,
    page: 0,
    page_size: MAX_DATASET_ROWS,
    sort: "asc",
  });
  return response.data.rows;
}
