import { Api } from "@/lib/api";

type GetFilteredTracesParams = {
  taskId: string;
  page: number;
  pageSize: number;
};

export async function getFilteredTraces(
  api: Api<unknown>,
  { taskId, page, pageSize }: GetFilteredTracesParams
) {
  const startTime = new Date();
  startTime.setDate(startTime.getDate() - 30);

  const response = await api.v1.querySpansV1TracesQueryGet({
    task_ids: [taskId],
    page,
    page_size: pageSize,
    sort: "desc",
    start_time: startTime.toISOString(),
  });

  return response.data;
}

type GetTraceParams = {
  taskId: string;
  traceId: string;
};

export async function getTrace(
  api: Api<unknown>,
  { taskId, traceId }: GetTraceParams
) {
  const response = await api.v1.querySpansV1TracesQueryGet({
    trace_ids: [traceId],
    task_ids: [taskId],
  });

  if (response.data.traces.length === 0) {
    return null;
  }

  return response.data.traces[0];
}
