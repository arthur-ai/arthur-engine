import { Api } from "@/lib/api-client/api-client";
import { Dataset } from "@/types/dataset";

export interface FetchDatasetsParams {
  dataset_name?: string;
  page: number;
  page_size: number;
  sort: "asc" | "desc";
}

export interface CreateDatasetParams {
  name: string;
  description: string | null;
  metadata: Record<string, unknown>;
}

export async function createDataset(
  api: Api<unknown>,
  taskId: string,
  formData: {
    name: string;
    description?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<Dataset> {
  const response = await api.api.createDatasetApiV2DatasetsPost({
    name: formData.name,
    description: formData.description ?? null,
    metadata: {
      task_id: taskId,
      ...formData.metadata,
    },
  });

  return response.data as Dataset;
}

export async function deleteDataset(
  api: Api<unknown>,
  datasetId: string
): Promise<void> {
  await api.api.deleteDatasetApiV2DatasetsDatasetIdDelete(datasetId);
}

export function buildFetchDatasetsParams(filters: {
  searchQuery?: string;
  sortOrder: "asc" | "desc";
  page: number;
  pageSize: number;
}): FetchDatasetsParams {
  return {
    dataset_name: filters.searchQuery || undefined,
    page: filters.page,
    page_size: filters.pageSize,
    sort: filters.sortOrder,
  };
}
