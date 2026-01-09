import { useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";
import { useTask } from "../useTask";

import { queryKeys } from "@/lib/queryKeys";

export const useTransforms = () => {
  const { api } = useApi()!;
  const { task } = useTask();

  return useQuery({
    queryKey: [queryKeys.transforms.list(task!.id)],
    queryFn: () =>
      api.listTransformsForTaskApiV1TasksTaskIdTracesTransformsGet({
        taskId: task!.id,
      }),
    select: (data) => data.data.transforms,
  });
};
