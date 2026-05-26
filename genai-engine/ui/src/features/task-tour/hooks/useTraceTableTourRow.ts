import { useLayoutEffect, useRef } from "react";

import { TOUR_IDS } from "../selectors";

/**
 * Tags the first body row of the shared-components `TracesTable` (Material React
 * Table) with `data-tour-id` for the task tour. The package table does not
 * accept row props, so we stamp the attribute after render and keep it in sync
 * when MRT virtualizes or re-renders rows.
 */
export function useTraceTableTourRow(hasRows: boolean, pageIndex: number, isLoading: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container || !hasRows || isLoading) return;

    const stampFirstRow = () => {
      const firstRow = container.querySelector("tbody tr");
      if (!firstRow) return;

      container.querySelectorAll(`[data-tour-id="${TOUR_IDS.tracesFirstRow}"]`).forEach((el) => {
        if (el !== firstRow) el.removeAttribute("data-tour-id");
      });

      if (firstRow.getAttribute("data-tour-id") !== TOUR_IDS.tracesFirstRow) {
        firstRow.setAttribute("data-tour-id", TOUR_IDS.tracesFirstRow);
      }
    };

    stampFirstRow();

    const observer = new MutationObserver(() => {
      stampFirstRow();
    });

    observer.observe(container, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-tour-id"] });

    return () => {
      observer.disconnect();
      container.querySelector(`[data-tour-id="${TOUR_IDS.tracesFirstRow}"]`)?.removeAttribute("data-tour-id");
    };
  }, [hasRows, pageIndex, isLoading]);

  return containerRef;
}
