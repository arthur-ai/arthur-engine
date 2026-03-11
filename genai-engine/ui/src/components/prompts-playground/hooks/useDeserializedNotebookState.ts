import { useQuery } from "@tanstack/react-query";

import { deserializeNotebookState } from "../utils/notebookStateUtils";

import { useApi } from "@/hooks/useApi";
import { useNotebookState } from "@/hooks/useNotebooks";
import { queryKeys } from "@/lib/queryKeys";

/**
 * TanStack Query hook that deserializes raw notebook state into frontend-ready
 * prompts, keywords, and the full state object.
 *
 * Wraps the async `deserializeNotebookState` utility (which fetches saved prompts
 * from the API) as a dependent query, so callers get a standard
 * { data, isLoading, error } interface instead of managing `.then()` chains.
 *
 * Uses `staleTime: Infinity` because deserialization generates new UUIDs —
 * refetching would replace the user's in-progress edits.
 */
export function useDeserializedNotebookState(notebookId: string | undefined, taskId: string | undefined) {
  const apiClient = useApi();
  const { state: rawState } = useNotebookState(notebookId);

  const { data, isLoading, error } = useQuery({
    // Key only by notebookId+taskId to avoid re-running deserialization on every auto-save.
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.notebooks.deserialized(notebookId, taskId),
    queryFn: () => deserializeNotebookState(rawState!, apiClient!, taskId!),
    enabled: !!rawState && !!apiClient && !!taskId,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  return {
    prompts: data?.prompts,
    keywords: data?.keywords,
    fullState: data?.fullState,
    rawState,
    isLoading,
    error,
  };
}
