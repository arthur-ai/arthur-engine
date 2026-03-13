import { type IncomingFilter, type TimeRange } from "@arthur/shared-components";

import { getStartDate, mapFiltersToRequest } from "@/components/traces/components/filtering/mapper";
import { Api } from "@/lib/api";
import type { TraceSortBy } from "@/lib/api-client/api-client";

type CommonParams = {
  taskId: string;
  page: number;
  pageSize: number;
  filters: IncomingFilter[];
  timeRange: TimeRange;
  sort?: "asc" | "desc";
  sortBy?: TraceSortBy;
};

// Traces

export type GetFilteredTracesParams = CommonParams;

export async function getFilteredTraces(
  api: Api<unknown>,
  { taskId, page, pageSize, filters, timeRange, sort = "desc", sortBy }: GetFilteredTracesParams
) {
  const startTime = getStartDate(timeRange);

  const response = await api.api.listTracesMetadataApiV1TracesGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    sort,
    ...(sortBy && { sort_by: sortBy }),
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

export async function getFilteredSpans(
  api: Api<unknown>,
  { taskId, page, pageSize, filters, timeRange, sort = "desc", sortBy }: GetFilteredSpansParams
) {
  const response = await api.api.listSpansMetadataApiV1TracesSpansGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    sort,
    ...(sortBy && { sort_by: sortBy }),
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

export async function getFilteredSessions(api: Api<unknown>, { taskId, page, pageSize, filters, timeRange, sort = "desc" }: GetSessionsParams) {
  const response = await api.api.listSessionsMetadataApiV1TracesSessionsGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    sort,
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
    sort: "asc",
  });
  return response.data;
}

// Users

export type GetUsersParams = CommonParams;

export async function getUsers(api: Api<unknown>, { taskId, page, pageSize, filters, timeRange, sort = "desc" }: GetUsersParams) {
  const response = await api.api.listUsersMetadataApiV1TracesUsersGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    sort,
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
