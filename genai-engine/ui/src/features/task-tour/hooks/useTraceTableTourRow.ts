import { useLayoutEffect, useRef } from "react";

import { TOUR_IDS } from "../selectors";

/**
 * Tags the first body row of the shared-components `TracesTable` (Material React
 * Table) with `data-tour-id` for the task tour. The package table does not
 * accept row props, so we stamp the attribute after render.
 */
export function useTraceTableTourRow(hasRows: boolean, pageIndex: number) {
  const containerRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container || !hasRows) return;

    const firstRow = container.querySelector("tbody tr");
    if (!firstRow) return;

    firstRow.setAttribute("data-tour-id", TOUR_IDS.tracesFirstRow);
    return () => {
      firstRow.removeAttribute("data-tour-id");
    };
  }, [hasRows, pageIndex]);

  return containerRef;
}
