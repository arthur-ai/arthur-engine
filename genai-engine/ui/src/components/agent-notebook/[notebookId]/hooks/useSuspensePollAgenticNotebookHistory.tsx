import { useSuspenseQuery } from "@tanstack/react-query";

import { agenticNotebookHistoryQueryOptions } from "../../hooks/useAgenticNotebookHistory";

import { useApi } from "@/hooks/useApi";
import { pollWhileAnyInProgress, POLL_INTERVAL } from "@/lib/polling";
import { PaginationParams } from "@/types/common";

export const useSuspensePollAgenticNotebookHistory = (notebookId: string, pagination?: PaginationParams) => {
  const api = useApi()!;

  return useSuspenseQuery({
    ...agenticNotebookHistoryQueryOptions({ api, notebookId, pagination }),
    refetchInterval: pollWhileAnyInProgress(
      (data) => data?.data.data,
      (item) => item.status,
      POLL_INTERVAL.FAST
    ),
  });
};
