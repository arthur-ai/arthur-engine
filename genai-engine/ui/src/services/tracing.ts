import {
  IncomingFilter,
  mapFiltersToRequest,
} from "@/components/traces/components/filtering/mapper";
import { Api } from "@/lib/api";

type GetFilteredTracesParams = {
  taskId: string;
  page: number;
  pageSize: number;
  filters: IncomingFilter[];
};

export async function getFilteredTraces(
  api: Api<unknown>,
  { taskId, page, pageSize, filters }: GetFilteredTracesParams
) {
  const startTime = new Date();
  startTime.setDate(startTime.getDate() - 30);

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

type GetFilteredSpansParams = {
  taskId: string;
  page: number;
  pageSize: number;
  filters: IncomingFilter[];
};

export async function getFilteredSpans(
  api: Api<unknown>,
  { taskId, page, pageSize, filters }: GetFilteredSpansParams
) {
  const response = await api.api.listSpansMetadataApiV1TracesSpansGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
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

// Sessions

type GetSessionsParams = {
  taskId: string;
  page: number;
  pageSize: number;
  filters: IncomingFilter[];
};

export async function getFitleredSessions(
  api: Api<unknown>,
  { taskId, page, pageSize, filters }: GetSessionsParams
) {
  const response = await api.api.listSessionsMetadataApiV1TracesSessionsGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    ...mapFiltersToRequest(filters),
  });
  return response.data;
}
