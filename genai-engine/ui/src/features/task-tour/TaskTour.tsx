import { useEffect, useMemo } from "react";

import { createTaskTourEmptyStatePredicate } from "./emptyState";
import { useTracesTourPrep } from "./prep/useTracesTourPrep";
import { registerTaskTourActionBridge, registerTaskTourTargetRefreshBridge } from "./tourActions";
import { useTaskTourEngine } from "./useTaskTourEngine";
import {
  CertificateWidget,
  ChecklistWidget,
  DatasetTargetWidget,
  EvaluateTargetWidget,
  IntroWidget,
  PromptTargetWidget,
  ResumeFabWidget,
  SectionCompleteWidget,
  SpotlightWidget,
  TaskTourFormPrefillWidget,
  TracesTargetWidget,
  TracesTourCleanupWidget,
} from "./widgets";

import { GuidedStepPopover, TourHost, TourProvider, useReactRouterNavigator } from "@/features/tour";
import { useApi } from "@/hooks/useApi";

export interface TaskTourProps {
  /** Required: the task the tour should bind its routes against. */
  taskId: string;
  /** Optional human-readable name displayed on the completion certificate. */
  workspaceLabel?: string;
}

/**
 * Top-level mount for the Evals 101 / ADLC tour. v1's shell is intentionally
 * tiny — it composes the engine (via `useTaskTourEngine`), the React-Router
 * navigator adapter, and a flat list of ad-hoc widgets inside a `TourHost`.
 *
 * All persistence, progress, intro / step / spotlight / FAB / certificate
 * logic lives in widgets keyed off the engine's state. v0's monolithic
 * `ChecklistTour` is gone; each concern is one widget that subscribes to the
 * piece of engine state it needs.
 */
export function TaskTour({ taskId, workspaceLabel }: TaskTourProps) {
  const navigator = useReactRouterNavigator();
  const api = useApi();
  const isEmpty = useMemo(() => createTaskTourEmptyStatePredicate(api, taskId), [api, taskId]);
  const { engine, statePlugin } = useTaskTourEngine({ taskId, isEmpty });

  // Wire the legacy `dispatchTourEvent` shim to the active engine. Keeps the
  // 19 product-side call sites compiling against the v0 import names while
  // routing actions through v1's typed engine bus.
  useEffect(() => {
    if (!engine) return;
    const teardownActionBridge = registerTaskTourActionBridge((name) => engine.emitAction(name));
    const teardownTargetRefreshBridge = registerTaskTourTargetRefreshBridge(() => engine.refreshTarget());
    return () => {
      teardownTargetRefreshBridge();
      teardownActionBridge();
    };
  }, [engine]);

  // Whenever the persisted status leaves `in-progress` — dismissed, completed,
  // skipped, or reset back to unseen — revert the checklist to its default
  // minimized state so the next run starts compact.
  useEffect(() => {
    return statePlugin.store.subscribe((state, prev) => {
      if (prev.snapshot.status === state.snapshot.status) return;
      if (state.snapshot.status !== "in-progress") {
        statePlugin.setSnapshot({ minimized: true });
      }
    });
  }, [statePlugin]);

  if (!engine) return null;
  return (
    <TourProvider tour={engine} navigator={navigator}>
      <TaskTourBody statePlugin={statePlugin} workspaceLabel={workspaceLabel} taskId={taskId} />
    </TourProvider>
  );
}

interface TaskTourBodyProps {
  statePlugin: ReturnType<typeof useTaskTourEngine>["statePlugin"];
  workspaceLabel?: string;
  taskId: string;
}

/**
 * Inner shell rendered under `<TourProvider>`. Lives here (rather than in
 * `TaskTour`) so the widgets that need `useTour*` hooks have access to the
 * engine context, and so the prep hook (which calls Query Client hooks) sits
 * inside the same provider tree as the rest of the tour subtree.
 */
function TaskTourBody({ statePlugin, workspaceLabel, taskId }: TaskTourBodyProps) {
  // Register the traces preparation hook (keyed by
  // `TASK_TOUR_PREPARATIONS.traceOpened`). The engine consults this on
  // `prepare: { key }` steps before resolving the spotlight target.
  useTracesTourPrep({ taskId });

  return (
    <TourHost>
      <DatasetTargetWidget />
      <EvaluateTargetWidget />
      <PromptTargetWidget />
      <TracesTargetWidget />
      <TracesTourCleanupWidget />
      <TaskTourFormPrefillWidget />
      <IntroWidget />
      <SectionCompleteWidget />
      <SpotlightWidget />
      <GuidedStepPopover />
      <ChecklistWidget statePlugin={statePlugin} />
      <ResumeFabWidget statePlugin={statePlugin} />
      <CertificateWidget workspaceLabel={workspaceLabel} />
    </TourHost>
  );
}
