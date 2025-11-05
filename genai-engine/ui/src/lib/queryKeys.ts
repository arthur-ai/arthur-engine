import { IncomingFilter } from "@/components/traces/components/filtering/mapper";

export const queryKeys = {
  datasets: {
    search: {
      all: () => ["getDatasetsApiV2DatasetsSearchGet"] as const,
      filtered: (filters: Record<string, unknown>) =>
        ["getDatasetsApiV2DatasetsSearchGet", filters] as const,
    },
    detail: (datasetId: string) =>
      ["getDatasetApiV2DatasetsDatasetIdGet", datasetId] as const,
    versions: (datasetId: string) =>
      [
        "getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet",
        { datasetId, latest_version_only: true, page: 0, page_size: 1 },
      ] as const,
  },
  datasetVersions: {
    // List of all versions for a dataset
    list: () =>
      ["getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet"] as const,
    listForDataset: (datasetId: string) =>
      [
        "getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet",
        { datasetId },
      ] as const,
    // Single version detail
    all: () =>
      [
        "getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet",
      ] as const,
    detail: (datasetId: string, versionNumber: number) =>
      [
        "getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet",
        { datasetId, versionNumber },
      ] as const,
    forDataset: (datasetId: string) =>
      [
        "getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet",
        { datasetId },
      ] as const,
  },
  spans: {
    listPaginated: (
      filters: IncomingFilter[],
      page: number,
      pageSize: number
    ) =>
      [
        "listSpansMetadataApiV1TracesSpansGet",
        filters,
        page,
        pageSize,
      ] as const,
    byId: (spanId: string) =>
      ["getSpanByIdApiV1TracesSpansSpanIdGet", spanId] as const,
  },
  sessions: {
    list: (filters: IncomingFilter[]) =>
      ["listSessionsMetadataApiV1TracesSessionsGet", filters] as const,
    listPaginated: (
      filters: IncomingFilter[],
      page: number,
      pageSize: number
    ) =>
      [
        "listSessionsMetadataApiV1TracesSessionsGet",
        filters,
        page,
        pageSize,
      ] as const,
    byId: (sessionId: string) =>
      ["getSessionTracesApiV1TracesSessionsSessionIdGet", sessionId] as const,
  },
  traces: {
    list: (filters: IncomingFilter[]) =>
      ["listTracesMetadataApiV1TracesGet", filters] as const,
    listPaginated: (
      filters: IncomingFilter[],
      page: number,
      pageSize: number
    ) => ["listTracesMetadataApiV1TracesGet", filters, page, pageSize] as const,
    byId: (traceId: string) =>
      ["getTraceByIdApiV1TracesTraceIdGet", traceId] as const,
  },
  users: {
    listPaginated: (page: number, pageSize: number) =>
      ["listUsersMetadataApiV1TracesUsersGet", page, pageSize] as const,
    byId: (userId: string) =>
      ["getUserDetailsApiV1TracesUsersUserIdGet", userId] as const,
  },
} as const;
