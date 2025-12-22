import {
  Api,
  DatasetResponse,
  NewDatasetRequest,
} from "@/lib/api-client/api-client";

export interface FetchDatasetsParams {
  taskId: string;
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
  const response = await api.api.createDatasetApiV2TasksTaskIdDatasetsPost(
    taskId,
    {
      name: formData.name,
      description: formData.description ?? null,
      metadata: formData.metadata,
    }
  );

  return response.data;
}

export async function deleteDataset(
  api: Api<unknown>,
  datasetId: string
): Promise<void> {
  await api.api.deleteDatasetApiV2DatasetsDatasetIdDelete(datasetId);
}

export function buildFetchDatasetsParams(
  taskId: string | undefined,
  filters: {
    searchQuery?: string;
    sortOrder: "asc" | "desc";
    page: number;
    pageSize: number;
  }
): FetchDatasetsParams {
  if (!taskId) {
    throw new Error("taskId is required");
  }
  return {
    taskId,
    dataset_name: filters.searchQuery || undefined,
    page: filters.page,
    page_size: filters.pageSize,
    sort: filters.sortOrder,
  };
}
