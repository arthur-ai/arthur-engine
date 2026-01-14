import { useSuspenseQuery } from "@tanstack/react-query";

import { agenticNotebookHistoryQueryOptions } from "../../hooks/useAgenticNotebookHistory";

import { useApi } from "@/hooks/useApi";
import { ExperimentStatus } from "@/lib/api-client/api-client";
import { PaginationParams } from "@/types/common";

const POLL_STATUSES: Set<ExperimentStatus> = new Set(["running", "queued"] satisfies readonly ExperimentStatus[]);

export const useSuspensePollAgenticNotebookHistory = (notebookId: string, pagination?: PaginationParams) => {
  const api = useApi()!;

  return useSuspenseQuery({
    ...agenticNotebookHistoryQueryOptions({ api, notebookId, pagination }),
    refetchInterval: (query) => {
      return query.state.data?.data.data.some((item) => POLL_STATUSES.has(item.status)) ? 1000 : false;
    },
  });
};
