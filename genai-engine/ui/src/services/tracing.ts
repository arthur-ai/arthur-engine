import { getStartDate, IncomingFilter, mapFiltersToRequest } from "@/components/traces/components/filtering/mapper";
import { TimeRange } from "@/components/traces/constants";
import { Api } from "@/lib/api";

type CommonParams = {
  taskId: string;
  page: number;
  pageSize: number;
  filters: IncomingFilter[];
  timeRange: TimeRange;
};

// Traces

export type GetFilteredTracesParams = CommonParams;

export async function getFilteredTraces(api: Api<unknown>, { taskId, page, pageSize, filters, timeRange }: GetFilteredTracesParams) {
  const startTime = getStartDate(timeRange);

  const response = await api.api.listTracesMetadataApiV1TracesGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    sort: "desc",
    start_time: startTime.toISOString(),
    ...mapFiltersToRequest(filters),
  });

  return response.data;
}

type GetTraceParams = {
  traceId: string;
};

export async function getTrace(api: Api<unknown>, { traceId }: GetTraceParams) {
  const response = await api.api.getTraceByIdApiV1TracesTraceIdGet(traceId);

  return response.data;
}

export async function computeTraceMetrics(api: Api<unknown>, { traceId }: GetTraceParams) {
  const response = await api.api.computeTraceMetricsApiV1TracesTraceIdMetricsGet(traceId);
  return response.data;
}

// Spans

export type GetFilteredSpansParams = CommonParams;

export async function getFilteredSpans(api: Api<unknown>, { taskId, page, pageSize, filters, timeRange }: GetFilteredSpansParams) {
  const response = await api.api.listSpansMetadataApiV1TracesSpansGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    start_time: getStartDate(timeRange).toISOString(),
    ...mapFiltersToRequest(filters),
  });

  return response.data;
}

type GetSpanParams = {
  spanId: string;
};

export async function getSpan(api: Api<unknown>, { spanId }: GetSpanParams) {
  const response = await api.api.getSpanByIdApiV1TracesSpansSpanIdGet(spanId);
  return response.data;
}

export async function computeSpanMetrics(api: Api<unknown>, { spanId }: GetSpanParams) {
  const response = await api.api.computeSpanMetricsApiV1TracesSpansSpanIdMetricsGet(spanId);
  return response.data;
}

// Sessions

export type GetSessionsParams = CommonParams;

export async function getFilteredSessions(api: Api<unknown>, { taskId, page, pageSize, filters, timeRange }: GetSessionsParams) {
  const response = await api.api.listSessionsMetadataApiV1TracesSessionsGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    start_time: getStartDate(timeRange).toISOString(),
    ...mapFiltersToRequest(filters),
  });
  return response.data;
}

type GetSessionParams = {
  sessionId: string;
};

export async function getSession(api: Api<unknown>, { sessionId }: GetSessionParams) {
  const response = await api.api.getSessionTracesApiV1TracesSessionsSessionIdGet({
    sessionId,
  });
  return response.data;
}

// Users

export type GetUsersParams = CommonParams;

export async function getUsers(api: Api<unknown>, { taskId, page, pageSize, filters, timeRange }: GetUsersParams) {
  const response = await api.api.listUsersMetadataApiV1TracesUsersGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    start_time: getStartDate(timeRange).toISOString(),
    ...mapFiltersToRequest(filters),
  });

  return response.data;
}

type GetUserParams = {
  taskId: string;
  userId: string;
};

export async function getUser(api: Api<unknown>, { taskId, userId }: GetUserParams) {
  const response = await api.api.getUserDetailsApiV1TracesUsersUserIdGet({
    userId,
    task_ids: [taskId],
  });
  return response.data;
}
