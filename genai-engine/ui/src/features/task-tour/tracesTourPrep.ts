import { TIME_RANGES } from "@arthur/shared-components";

import { TOUR_IDS, tourSelector, type TourId } from "./selectors";

import { resolveTargetAsync } from "@/features/tour/core/targets";
import type { Api } from "@/lib/api";
import type { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredTraces } from "@/services/tracing";

const DRAWER_STEPS = new Set(["review-spans", "review-annotations", "add-feedback"]);

const STEP_TARGET: Record<string, TourId> = {
  "open-trace": TOUR_IDS.tracesFirstRow,
  "review-spans": TOUR_IDS.traceDrawerSpans,
  "review-annotations": TOUR_IDS.traceDrawerEvals,
  "add-feedback": TOUR_IDS.traceDrawerFeedback,
};

/** Long enough for route mount + lazy drawer chunk + trace suspense query. */
const TARGET_WAIT_MS = 20_000;

type TracesListPayload = {
  traces?: TraceMetadataResponse[];
};

export type TracesTourPrepDeps = {
  taskId: string;
  api: Api<unknown> | null;
  getDrawerTarget: () => { target: string; id: string | null };
  setDrawerTarget: (value: { target: "trace"; id: string }) => void;
  setPaginationContext: (value: { type: "trace"; ids: string[] }) => void;
  readFirstTraceFromCache: () => { traceId: string; traceIds: string[] } | null;
};

let prepDeps: TracesTourPrepDeps | null = null;

export function registerTracesTourPrepDeps(deps: TracesTourPrepDeps | null): void {
  prepDeps = deps;
}

function waitForTourTarget(tourId: TourId): Promise<Element | null> {
  return resolveTargetAsync({ kind: "selector", selector: tourSelector(tourId) }, { timeoutMs: TARGET_WAIT_MS });
}

async function ensureFirstTraceOpen(deps: TracesTourPrepDeps): Promise<void> {
  const drawer = deps.getDrawerTarget();
  if (drawer.id && drawer.target === "trace") return;

  let traceId: string | null = null;
  let traceIds: string[] = [];

  const cached = deps.readFirstTraceFromCache();
  if (cached) {
    traceId = cached.traceId;
    traceIds = cached.traceIds;
  } else if (deps.api) {
    const data = await getFilteredTraces(deps.api, {
      taskId: deps.taskId,
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

  deps.setPaginationContext({
    type: "trace",
    ids: traceIds.length > 0 ? traceIds : [traceId],
  });
  deps.setDrawerTarget({ target: "trace", id: traceId });
}

/**
 * Runs after the tour navigates to `/traces` and before the engine resolves the
 * step spotlight target. Waits for lazy-mounted trace UI (table rows, drawer
 * slot wrappers) so `data-tour-id` anchors exist when targeting runs.
 */
export async function prepareTracesTourStep(stepId: string): Promise<void> {
  const deps = prepDeps;
  const targetId = STEP_TARGET[stepId];
  if (!deps || !targetId) return;

  if (DRAWER_STEPS.has(stepId)) {
    await ensureFirstTraceOpen(deps);
  }

  await waitForTourTarget(targetId);
}

export function createReadFirstTraceFromCache(
  getQueriesData: (filters: { queryKey: readonly string[] }) => Array<[unknown, TracesListPayload | undefined]>
) {
  return (): { traceId: string; traceIds: string[] } | null => {
    const entries = getQueriesData({ queryKey: queryKeys.traces.list });
    for (const [, data] of entries) {
      const traces = data?.traces;
      const traceId = traces?.[0]?.trace_id;
      if (traceId) {
        return { traceId, traceIds: traces!.map((trace) => trace.trace_id) };
      }
    }
    return null;
  };
}
