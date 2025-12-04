import type { GetFilteredSpansParams, GetFilteredTracesParams, GetSessionsParams, GetUsersParams } from "@/services/tracing";

export const queryKeys = {
  datasets: {
    search: {
      all: () => ["getDatasetsApiV2TasksTaskIdDatasetsSearchGet"] as const,
      filtered: (filters: Record<string, unknown>) => ["getDatasetsApiV2TasksTaskIdDatasetsSearchGet", filters] as const,
    },
    detail: (datasetId: string) => ["getDatasetApiV2DatasetsDatasetIdGet", datasetId] as const,
    versions: (datasetId: string) =>
      ["getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet", { datasetId, latest_version_only: true, page: 0, page_size: 1 }] as const,
  },
  datasetVersions: {
    // List of all versions for a dataset
    list: () => ["getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet"] as const,
    listForDataset: (datasetId: string) => ["getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet", { datasetId }] as const,
    // Single version detail
    all: () => ["getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet"] as const,
    detail: (datasetId: string, versionNumber: number) =>
      ["getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet", { datasetId, versionNumber }] as const,
    forDataset: (datasetId: string) => ["getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet", { datasetId }] as const,
  },
  spans: {
    listPaginated: (params: GetFilteredSpansParams) => ["listSpansMetadataApiV1TracesSpansGet", params] as const,
    byId: (spanId: string) => ["getSpanByIdApiV1TracesSpansSpanIdGet", spanId] as const,
  },
  sessions: {
    listPaginated: (params: GetSessionsParams) => ["listSessionsMetadataApiV1TracesSessionsGet", params] as const,
    byId: (sessionId: string) => ["getSessionTracesApiV1TracesSessionsSessionIdGet", sessionId] as const,
  },
  traces: {
    listPaginated: (params: GetFilteredTracesParams) => ["listTracesMetadataApiV1TracesGet", params] as const,
    list: ["listTracesMetadataApiV1TracesGet"] as const,
    byId: (traceId: string) => ["getTraceByIdApiV1TracesTraceIdGet", traceId] as const,
  },
  users: {
    listPaginated: (params: GetUsersParams) => ["listUsersMetadataApiV1TracesUsersGet", params] as const,
    byId: (userId: string) => ["getUserDetailsApiV1TracesUsersUserIdGet", userId] as const,
  },
  ragProviders: {
    all: () => ["getRagProvidersApiV1TasksTaskIdRagProvidersGet"] as const,
    list: (taskId: string) => ["getRagProvidersApiV1TasksTaskIdRagProvidersGet", { taskId }] as const,
  },
  ragCollections: {
    all: () => ["listRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGet"] as const,
    list: (providerId: string) => ["listRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGet", { providerId }] as const,
  },
} as const;
