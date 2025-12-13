import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { ContinuousEvalCreateRequest } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export const useCreateContinuousEval = () => {
  const api = useApi()!;
  const { task } = useTask();

  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ContinuousEvalCreateRequest) => {
      const response = await api.api.createContinuousEvalApiV1TasksTaskIdContinuousEvalsPost(task!.id, data);

      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [queryKeys.continuousEvals.all(task!.id)] });
    },
  });
};
