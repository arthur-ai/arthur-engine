import { TIME_RANGES } from "@arthur/shared-components";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useRef } from "react";

import { TASK_TOUR_PREPARATIONS } from "../content/wiring";
import { TASK_TOUR_OCCLUDERS } from "../occluders";
import { tourSelector, TOUR_IDS, type TourId } from "../selectors";

import { useDrawerTarget } from "@/components/traces/hooks/useDrawerTarget";
import { usePaginationContext } from "@/components/traces/stores/pagination-context";
import { resolveTargetAsync } from "@/features/tour";
import { useRegisterOccluder, useRegisterPreparation } from "@/features/tour";
import type { OccluderDescriptor, PreparationHook } from "@/features/tour";
import { useApi } from "@/hooks/useApi";
import type { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredTraces } from "@/services/tracing";

/** Long enough for route mount + lazy drawer chunk + trace suspense query. */
const TARGET_WAIT_MS = 20_000;

// Every trace-section step whose target lives inside the trace drawer, so the
// prep hook must open the first trace before resolving. Includes the
// dataset-capture beats (review-trace-actions / open-add-to-dataset /
// save-trace-to-dataset), which all declare `prepareKey: traceOpened` in
// wiring.ts and depend on the drawer being open on resume / re-entry.
const DRAWER_STEPS = new Set([
  "review-spans",
  "review-annotations",
  "add-feedback",
  "review-trace-actions",
  "open-add-to-dataset",
  "save-trace-to-dataset",
]);

// Static `data-tour-id` anchors the prep hook waits for before resolving. Only
// listed for the selector-targeted steps — the dataset-capture beats above are
// queryHook-resolved, so a static fallback wait here would block up to
// TARGET_WAIT_MS before the engine's own awaitTarget even runs. Leave them out.
const STEP_TARGET_FALLBACK: Record<string, TourId> = {
  "open-trace": TOUR_IDS.tracesFirstRow,
  "review-spans": TOUR_IDS.traceDrawerSpans,
  "review-annotations": TOUR_IDS.traceDrawerEvals,
  "add-feedback": TOUR_IDS.traceDrawerFeedback,
};

type TracesListPayload = { traces?: TraceMetadataResponse[] };

export interface UseTracesTourPrepOptions {
  taskId: string;
}

/**
 * Replaces v0's global `prepDeps` singleton with a properly scoped React
 * hook. Called directly from `TaskTourPortal` (in `TaskTour.tsx`) inside
 * `<TourHost>`:
 *  - Reads trace-drawer + pagination state through their respective hooks.
 *  - Registers a preparation hook against the engine via
 *    {@link useRegisterPreparation} so trace-section steps run it before
 *    target resolution.
 *
 * Behaviour:
 *  1. Engine fires the prep request after navigation to `/traces`.
 *  2. The hook opens the first trace drawer (if not already open) for the
 *     drawer-targeted steps, populating pagination context so the trace
 *     drawer's prev/next nav works.
 *  3. It then waits up to `TARGET_WAIT_MS` for the step's target to land in
 *     the DOM (the fallback `data-tour-id` selector — the queryHook variant
 *     short-circuits once the live ref fires).
 *  4. Resolves `{ ready: true }` so the engine resumes the normal target-
 *     resolution path.
 */
export function useTracesTourPrep({ taskId }: UseTracesTourPrepOptions): void {
  const api = useApi();
  const queryClient = useQueryClient();
  const [drawerTarget, setDrawerTarget] = useDrawerTarget();
  const drawerTargetRef = useRef(drawerTarget);
  drawerTargetRef.current = drawerTarget;
  const setPaginationContext = usePaginationContext((state) => state.actions.setContext);

  // Stash everything the prep hook needs in refs so the registered hook
  // closure stays referentially stable across re-renders — re-registering on
  // every render would cause the engine's `registerPreparation` Map to
  // churn but is otherwise harmless.
  const apiRef = useRef(api);
  apiRef.current = api;
  const setDrawerTargetRef = useRef(setDrawerTarget);
  setDrawerTargetRef.current = setDrawerTarget;
  const setPaginationContextRef = useRef(setPaginationContext);
  setPaginationContextRef.current = setPaginationContext;
  const queryClientRef = useRef(queryClient);
  queryClientRef.current = queryClient;
  const taskIdRef = useRef(taskId);
  taskIdRef.current = taskId;

  const ensureFirstTraceOpen = useCallback(async (): Promise<void> => {
    const drawer = drawerTargetRef.current;
    if (drawer.id && drawer.target === "trace") return;

    let traceId: string | null = null;
    let traceIds: string[] = [];

    // Try cache first to avoid an unnecessary refetch.
    const cachedEntries = queryClientRef.current.getQueriesData<TracesListPayload>({
      queryKey: queryKeys.traces.list,
    });
    for (const [, data] of cachedEntries) {
      const traces = data?.traces;
      const tid = traces?.[0]?.trace_id;
      if (tid) {
        traceId = tid;
        traceIds = traces!.map((t) => t.trace_id);
        break;
      }
    }

    if (!traceId && apiRef.current) {
      const data = await getFilteredTraces(apiRef.current, {
        taskId: taskIdRef.current,
        page: 0,
        pageSize: FETCH_SIZE,
        filters: [],
        timeRange: TIME_RANGES["1 month"],
        sort: "desc",
        sortBy: "start_time",
      });
      traceId = data.traces?.[0]?.trace_id ?? null;
      traceIds = data.traces?.map((trace) => trace.trace_id) ?? [];
    }

    if (!traceId) return;

    setPaginationContextRef.current({
      type: "trace",
      ids: traceIds.length > 0 ? traceIds : [traceId],
    });
    setDrawerTargetRef.current({ target: "trace", id: traceId });
  }, []);

  const hook = useCallback<PreparationHook>(
    async ({ stepContext }) => {
      const fallbackTarget = STEP_TARGET_FALLBACK[stepContext.stepId];

      if (DRAWER_STEPS.has(stepContext.stepId)) {
        await ensureFirstTraceOpen();
      }

      // Best-effort: wait for the static DOM anchor. queryHook-resolved
      // steps will be re-checked by the engine on top of this, so the
      // worst case here is we wait the full timeout when the anchor is
      // missing — which already matches v0's behaviour.
      if (fallbackTarget) {
        await resolveTargetAsync({ kind: "selector", selector: tourSelector(fallbackTarget) }, { timeoutMs: TARGET_WAIT_MS });
      }

      return { ready: true };
    },
    [ensureFirstTraceOpen]
  );

  useRegisterPreparation(TASK_TOUR_PREPARATIONS.traceOpened, hook);

  // Register the trace drawer as a close-only occluder. Opening stays owned by
  // the prep hook (it needs an async-resolved trace id), so `open` is omitted —
  // drawer steps declare it via `surfaces.open` (auto-derived from
  // `prepareKey: traceOpened`) so reconcile leaves it alone, while every other
  // step closes a stranded drawer on entry. Close clears the nuqs params with
  // `history: "replace"` so it doesn't pollute the back button mid-tour, and
  // returns the setter promise so reconcile can await the URL clear before the
  // engine's same-route match check.
  const occluder = useMemo<OccluderDescriptor>(
    () => ({
      id: TASK_TOUR_OCCLUDERS.traceDrawer,
      isOpen: () => Boolean(drawerTargetRef.current.id),
      close: () => setDrawerTargetRef.current({ id: null }, { history: "replace" }),
    }),
    []
  );
  useRegisterOccluder(occluder);
}
