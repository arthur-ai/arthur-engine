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
} as const;
