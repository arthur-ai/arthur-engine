import {
  Api,
  DatasetResponse,
  NewDatasetRequest,
} from "@/lib/api-client/api-client";

export interface FetchDatasetsParams {
  dataset_name?: string;
  page: number;
  page_size: number;
  sort: "asc" | "desc";
}

export async function createDataset(
  api: Api<unknown>,
  taskId: string,
  formData: NewDatasetRequest
): Promise<DatasetResponse> {
  const response = await api.api.createDatasetApiV2DatasetsPost({
    name: formData.name,
    description: formData.description ?? null,
    metadata: {
      task_id: taskId,
      ...formData.metadata,
    },
  });

  return response.data;
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
