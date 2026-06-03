import { useEffect, useMemo, type ReactNode } from "react";

import { TourSidePanel } from "./components/TourSidePanel";
import { createTaskTourEmptyStatePredicate } from "./emptyState";
import { useTracesTourPrep } from "./prep/useTracesTourPrep";
import { registerTaskTourActionBridge, registerTaskTourTargetRefreshBridge } from "./tourActions";
import { useTaskTourEngine } from "./useTaskTourEngine";
import {
  CertificateWidget,
  DatasetTargetWidget,
  EvaluateTargetWidget,
  IntroWidget,
  PromptTargetWidget,
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
  /**
   * The page chrome the tour wraps — typically the route's `<main>`. Rendered
   * as a flex sibling of {@link TourSidePanel} so the docked panel takes window
   * space away from the page rather than floating over it.
   */
  children: ReactNode;
}

/**
 * Top-level mount for the Evals 101 / ADLC tour. It owns the engine (via
 * `useTaskTourEngine`) and the React-Router navigator adapter, then provides
 * the tour context to three siblings:
 *
 *  1. `children` — the page (`<main>`), a flex child of the layout row.
 *  2. `<TourSidePanel>` — the in-flow, collapsible docked panel that hosts the
 *     persistent checklist / resume surfaces (formerly floating widgets).
 *  3. `<TaskTourPortal>` — the element-anchored overlays (spotlight, tooltips,
 *     intro / section-complete / certificate dialogs) that remain portaled to
 *     `document.body`.
 *
 * All persistence, progress, intro / step / spotlight / certificate logic
 * lives in widgets keyed off the engine's state.
 */
export function TaskTour({ taskId, workspaceLabel, children }: TaskTourProps) {
  const navigator = useReactRouterNavigator();
  const api = useApi();
  const isEmpty = useMemo(() => createTaskTourEmptyStatePredicate(api, taskId), [api, taskId]);
  const { engine, statePlugin } = useTaskTourEngine({ taskId, isEmpty });

  // Wire the legacy `dispatchTourEvent` shim to the active engine. Keeps the
  // product-side call sites compiling against the v0 import names while routing
  // actions through v1's typed engine bus.
  useEffect(() => {
    if (!engine) return;
    const teardownActionBridge = registerTaskTourActionBridge((name) => engine.emitAction(name));
    const teardownTargetRefreshBridge = registerTaskTourTargetRefreshBridge(() => engine.refreshTarget());
    return () => {
      teardownTargetRefreshBridge();
      teardownActionBridge();
    };
  }, [engine]);

  // Engine init can fail / be mid-mount; still render the page so the layout
  // never blanks out.
  if (!engine) return <>{children}</>;
  return (
    <TourProvider tour={engine} navigator={navigator}>
      {children}
      <TourSidePanel statePlugin={statePlugin} />
      <TaskTourPortal workspaceLabel={workspaceLabel} taskId={taskId} />
    </TourProvider>
  );
}

interface TaskTourPortalProps {
  workspaceLabel?: string;
  taskId: string;
}

/**
 * Element-anchored overlays portaled to `document.body`. Lives under
 * `<TourProvider>` so the widgets (and the traces prep hook, which calls Query
 * Client hooks) share the engine context. The persistent checklist + resume
 * surfaces are NOT here — they render in-flow via {@link TourSidePanel}.
 */
function TaskTourPortal({ workspaceLabel, taskId }: TaskTourPortalProps) {
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
      <CertificateWidget workspaceLabel={workspaceLabel} />
    </TourHost>
  );
}
