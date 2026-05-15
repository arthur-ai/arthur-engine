import type { GetFilteredSpansParams, GetFilteredTracesParams, GetSessionsParams, GetUsersParams } from "@/services/tracing";
import type { TimeInterval } from "@/utils/timeWindows";

export const queryKeys = {
  prompts: {
    variables: (name: string, versions: number[]) => ["promptsVariables", { name, versions }] as const,
  },
  metrics: {
    overview: (taskId: string, interval: TimeInterval, timezone?: string) => ["taskOverviewMetrics", { taskId, interval, timezone }] as const,
  },
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
  continuousEvals: {
    all: (taskId: string) => ["listContinuousEvalsApiV1TasksTaskIdContinuousEvalsGet", { taskId }] as const,
    byId: (evalId: string) => ["getContinuousEvalByIdApiV1ContinuousEvalsEvalIdGet", { evalId }] as const,
    results: (taskId: string) => ["listContinuousEvalRunResultsApiV1TasksTaskIdContinuousEvalsResultsGet", { taskId }] as const,
    variableMapping: (taskId: string, transformId: string, evalName: string, evalVersion: string) =>
      [
        "getContinuousEvalVariablesAndMappingsApiV1TasksTaskIdContinuousEvalsTransformsTransformIdLlmEvalsEvalNameVersionsEvalVersionVariablesGet",
        { taskId, transformId, evalName, evalVersion },
      ] as const,
    testRuns: {
      byEval: (evalId: string) => ["listTestRunsApiV1ContinuousEvalsEvalIdTestRunsGet", { evalId }] as const,
      byId: (testRunId: string) => ["getTestRunApiV1ContinuousEvalsTestRunsTestRunIdGet", { testRunId }] as const,
      results: (testRunId: string) => ["getTestRunResultsApiV1ContinuousEvalsTestRunsTestRunIdResultsGet", { testRunId }] as const,
    },
  },
  transforms: {
    list: (taskId: string) => ["listTransformsApiV1TasksTaskIdTracesTransformsGet", { taskId }] as const,
    byId: (transformId: string) => ["getTransformApiV1TracesTransformsTransformIdGet", { transformId }] as const,
    versions: (transformId: string) => ["listTransformVersionsApiV1TracesTransformsTransformIdVersionsGet", { transformId }] as const,
    version: (transformId: string, versionId: string) =>
      ["getTransformVersionApiV1TracesTransformsTransformIdVersionsVersionIdGet", { transformId, versionId }] as const,
  },
  annotations: {
    byId: (annotationId: string) => ["getAnnotationByIdApiV1AnnotationsAnnotationIdGet", { annotationId }] as const,
  },
  agentExperiments: {
    all: (taskId: string) => ["listAgenticExperimentsApiV1TasksTaskIdAgenticExperimentsGet", { taskId }] as const,
    byId: (experimentId: string) => ["getAgenticExperimentApiV1AgenticExperimentsExperimentIdGet", { experimentId }] as const,
    testCases: (experimentId: string) => ["getAgenticExperimentTestCasesApiV1AgenticExperimentsExperimentIdTestCasesGet", { experimentId }] as const,
    endpoints: {
      all: () => ["listAgentExperimentEndpointsApiV1AgentExperimentsEndpointsGet"] as const,
      byId: (endpointId: string) => ["getAgentExperimentEndpointByIdApiV1AgentExperimentsEndpointsEndpointIdGet", { endpointId }] as const,
    },
  },
  agentNotebooks: {
    all: (taskId: string) => ["listAgenticNotebooksApiV1TasksTaskIdAgenticNotebooksGet", { taskId }] as const,
    byId: (notebookId: string) => ["getAgenticNotebookApiV1AgenticNotebooksNotebookIdGet", { notebookId }] as const,
    history: (notebookId: string) => ["getAgenticNotebookHistoryApiV1AgenticNotebooksNotebookIdHistoryGet", { notebookId }] as const,
  },
  ragNotebooks: {
    // Prefix matchers for invalidation (no params = matches all queries with this method)
    listAll: () => ["listRagNotebooksApiV1TasksTaskIdRagNotebooksGet"] as const,
    detailAll: () => ["getRagNotebookApiV1RagNotebooksNotebookIdGet"] as const,
    stateAll: () => ["getRagNotebookStateApiV1RagNotebooksNotebookIdStateGet"] as const,
    historyAll: () => ["getRagNotebookHistoryApiV1RagNotebooksNotebookIdHistoryGet"] as const,
    // Specific queries with params
    list: (taskId: string) => ["listRagNotebooksApiV1TasksTaskIdRagNotebooksGet", { taskId }] as const,
    detail: (notebookId: string) => ["getRagNotebookApiV1RagNotebooksNotebookIdGet", notebookId] as const,
    state: (notebookId: string) => ["getRagNotebookStateApiV1RagNotebooksNotebookIdStateGet", notebookId] as const,
    history: (notebookId: string) => ["getRagNotebookHistoryApiV1RagNotebooksNotebookIdHistoryGet", notebookId] as const,
  },
  ragExperiments: {
    // Prefix matchers for invalidation
    listAll: () => ["listRagExperimentsApiV1TasksTaskIdRagExperimentsGet"] as const,
    detailAll: () => ["getRagExperimentApiV1RagExperimentsExperimentIdGet"] as const,
    testCasesAll: () => ["getRagExperimentTestCasesApiV1RagExperimentsExperimentIdTestCasesGet"] as const,
    // Specific queries with params
    list: (taskId: string) => ["listRagExperimentsApiV1TasksTaskIdRagExperimentsGet", { taskId }] as const,
    detail: (experimentId: string) => ["getRagExperimentApiV1RagExperimentsExperimentIdGet", experimentId] as const,
    testCases: (experimentId: string, page: number, pageSize: number) =>
      ["getRagExperimentTestCasesApiV1RagExperimentsExperimentIdTestCasesGet", { experimentId, page, pageSize }] as const,
  },
  ragSearchSettings: {
    load: (configId: string, versionNumber?: number) => ["loadRagConfig", configId, versionNumber] as const,
  },
  notebooks: {
    deserialized: (notebookId: string | undefined, taskId: string | undefined) => ["notebookDeserialized", notebookId, taskId] as const,
  },
  providers: {
    all: () => ["getModelProvidersApiV1ModelProvidersGet"] as const,
    availableModels: (providers: string[]) => ["availableModels", ...providers] as const,
  },
  taskMetrics: {
    all: (taskId: string) => ["taskMetrics", "all", taskId] as const,
  },
  tasks: {
    all: () => ["searchTasksApiV2TasksSearchPost"] as const,
    list: () => ["searchTasksApiV2TasksSearchPost", "active"] as const,
    archived: () => ["searchTasksApiV2TasksSearchPost", "archived"] as const,
  },
} as const;
