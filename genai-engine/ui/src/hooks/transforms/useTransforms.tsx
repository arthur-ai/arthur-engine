import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";
import { useTask } from "../useTask";

import type { Api, ListTransformsForTaskApiV1TasksTaskIdTracesTransformsGetParams } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

type Params = Omit<ListTransformsForTaskApiV1TasksTaskIdTracesTransformsGetParams, "taskId">;

export const transformsQueryOptions = ({ api, params = { page_size: 1000 }, taskId }: { api: Api<unknown>; taskId: string; params?: Params }) =>
  queryOptions({
    queryKey: [...queryKeys.transforms.list(taskId), params],
    queryFn: () =>
      api.api.listTransformsForTaskApiV1TasksTaskIdTracesTransformsGet({
        taskId,
        ...params,
      }),
    select: (data) => data.data,
  });

export const useTransforms = (params: Params = {}) => {
  const api = useApi()!;
  const { task } = useTask();

  return useQuery(transformsQueryOptions({ api, params, taskId: task!.id }));
};
