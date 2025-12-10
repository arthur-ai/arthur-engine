import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";

export const useContinuousEvals = () => {
  const { task } = useTask();
  const api = useApi()!;

  return useQuery({
    queryKey: [queryKeys.continuousEvals.all(task!.id)],
    queryFn: () => api.api.listContinuousEvalsApiV1TasksTaskIdContinuousEvalsGet({ taskId: task!.id }),
    select: (data) => data.data,
  });
};
