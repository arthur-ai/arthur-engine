import React, { useEffect, useRef, useState } from "react";

import { computeRowPage } from "./rowLocation";

import { MAX_DATASET_ROWS } from "@/constants/datasetConstants";
import type { DatasetAction } from "@/contexts/dataset";
import { TOUR_IDS } from "@/features/task-tour/selectors";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { DatasetVersionResponse, DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { track } from "@/services/analytics";

interface UseDeepLinkedRowParams {
  datasetId: string;
  /** Current `?row=` URL param. Only its value at mount matters. */
  rowId: string | null;
  taskId: string | undefined;
  currentVersion: number | undefined;
  /** Server rows of the currently displayed table page. */
  rows: DatasetVersionRowResponse[];
  versionLoading: boolean;
  rowsPerPage: number;
  currentPage: number;
  dispatch: React.Dispatch<DatasetAction>;
}

// Owns deep-link row arrival (`?row=` present at mount — in-page drawer opens target
// rows that are already on screen): tracks the arrival, locates the row's table page,
// jumps to it, scrolls it into view and flashes it once. Datasets are capped at
// MAX_DATASET_ROWS, so one full fetch (same ordering as the table query) locates the
// row client-side.
export function useDeepLinkedRow({
  datasetId,
  rowId,
  taskId,
  currentVersion,
  rows,
  versionLoading,
  rowsPerPage,
  currentPage,
  dispatch,
}: UseDeepLinkedRowParams): { highlightedRowId: string | null } {
  const targetRef = useRef(rowId);
  const [phase, setPhase] = useState<"locating" | "awaitingRender" | "done">(rowId ? "locating" : "done");
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
    enabled: phase === "locating" && !!datasetId && currentVersion !== undefined,
  });
  const allRows = (data as DatasetVersionResponse | undefined)?.rows;

  // Jump to the located page, or bail when the row isn't in this version.
  useEffect(() => {
    if (phase !== "locating" || !allRows) return;
    const target = targetRef.current;
    const page = target
      ? computeRowPage(
          allRows.map((r) => r.id),
          target,
          rowsPerPage
        )
      : null;
    if (page === null) {
      // Stale link — the row drawer shows its own not-found state.
      setPhase("done");
      return;
    }
    if (page !== currentPage) {
      dispatch({ type: "VIEW/SET_PAGE", payload: page });
    }
    setPhase("awaitingRender");
  }, [phase, allRows, rowsPerPage, currentPage, dispatch]);

  // Once the target page has rendered, scroll to the row and flash it.
  useEffect(() => {
    if (phase !== "awaitingRender" || versionLoading) return;
    const target = targetRef.current;
    if (!target || !rows.some((r) => r.id === target)) return;
    const frame = window.requestAnimationFrame(() => {
      document
        .querySelector(`[data-tour-id="${TOUR_IDS.datasetTable}"]`)
        ?.querySelector(`[data-row-id="${CSS.escape(target)}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    setHighlightedRowId(target);
    setPhase("done");
    return () => window.cancelAnimationFrame(frame);
  }, [phase, versionLoading, rows]);

  // One-shot flash: clear after the animation has finished.
  useEffect(() => {
    if (!highlightedRowId) return;
    const timeout = window.setTimeout(() => setHighlightedRowId(null), 2500);
    return () => window.clearTimeout(timeout);
  }, [highlightedRowId]);

  return { highlightedRowId };
}
