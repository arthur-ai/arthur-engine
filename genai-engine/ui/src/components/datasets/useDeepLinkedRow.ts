import React, { useCallback, useEffect, useRef, useState } from "react";

import { computeRowPage } from "./rowLocation";

import { MAX_DATASET_ROWS } from "@/constants/datasetConstants";
import type { DatasetAction } from "@/contexts/dataset";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { DatasetVersionResponse } from "@/lib/api-client/api-client";
import { track } from "@/services/analytics";

interface UseDeepLinkedRowParams {
  datasetId: string;
  /** Current `?row=` URL param. Only its value at mount matters. */
  rowId: string | null;
  taskId: string | undefined;
  currentVersion: number | undefined;
  rowsPerPage: number;
  currentPage: number;
  dispatch: React.Dispatch<DatasetAction>;
}

// Owns deep-link row arrival (`?row=` present at mount — in-page drawer opens target
// rows that are already on screen): tracks the arrival, locates the row's table page
// and jumps to it, then flags the row as highlighted. Scrolling and the flash are the
// row's own responsibility (DatasetTableRow reacts to `isHighlighted`), so this hook
// never touches the DOM. Datasets are capped at MAX_DATASET_ROWS, so one full fetch
// (same ordering as the table query) locates the row client-side.
export function useDeepLinkedRow({ datasetId, rowId, taskId, currentVersion, rowsPerPage, currentPage, dispatch }: UseDeepLinkedRowParams): {
  highlightedRowId: string | null;
  clearHighlight: () => void;
} {
  const targetRef = useRef(rowId);
  const locatedRef = useRef(false);
  const [highlightedRowId, setHighlightedRowId] = useState<string | null>(null);

  // Track once the task resolves (it loads async) so the event carries a real task_id.
  const trackedRef = useRef(false);
  useEffect(() => {
    if (trackedRef.current || !targetRef.current || !taskId) return;
    trackedRef.current = true;
    track("dataset/row_drawer_opened", { dataset_id: datasetId, task_id: taskId, source: "deep_link" });
  }, [taskId, datasetId]);

  const { data } = useApiQuery<"getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet">({
    method: "getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet",
    args: [
      {
        datasetId,
        versionNumber: currentVersion!,
        page: 0,
        page_size: MAX_DATASET_ROWS,
        sort: "asc",
      },
    ] as const,
    enabled: !!targetRef.current && !!datasetId && currentVersion !== undefined,
  });
  const allRows = (data as DatasetVersionResponse | undefined)?.rows;

  // Locate once: jump to the row's page and flag it. A stale link (row not in this
  // version) does nothing — the row drawer shows its own not-found state.
  useEffect(() => {
    const target = targetRef.current;
    if (!target || locatedRef.current || !allRows) return;
    locatedRef.current = true;
    const page = computeRowPage(
      allRows.map((r) => r.id),
      target,
      rowsPerPage
    );
    if (page === null) return;
    if (page !== currentPage) {
      dispatch({ type: "VIEW/SET_PAGE", payload: page });
    }
    setHighlightedRowId(target);
  }, [allRows, rowsPerPage, currentPage, dispatch]);

  const clearHighlight = useCallback(() => setHighlightedRowId(null), []);

  return { highlightedRowId, clearHighlight };
}
