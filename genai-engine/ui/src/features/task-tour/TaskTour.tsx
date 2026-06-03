import { useEffect, useMemo } from "react";

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
}

/**
 * Top-level mount for the Evals 101 / ADLC tour. A **sidecar**: it owns the
 * engine (via `useTaskTourEngine`) and the React-Router navigator, and renders
 * only the tour's own surfaces — it does NOT wrap the page. `TaskLayout` renders
 * the page (`<main>`) as a sibling and lazy-loads this component, so the page
 * never waits on (or remounts behind) the tour chunk. The product page talks to
 * the tour through the global `dispatchTourEvent` bridge + `data-tour-id`
 * attributes, never tour React context, so it doesn't need to be under
 * `<TourProvider>`.
 *
 * Two siblings render under the provider:
 *  1. `<TourSidePanel>` — the in-flow, collapsible docked panel (checklist /
 *     resume), a flex sibling of the page `<main>`.
 *  2. `<TaskTourPortal>` — element-anchored overlays (spotlight, popovers,
 *     intro / section-complete / certificate dialogs) portaled to `document.body`.
 */
export function TaskTour({ taskId }: TaskTourProps) {
  const navigator = useReactRouterNavigator();
  const api = useApi();
  const isEmpty = useMemo(() => createTaskTourEmptyStatePredicate(api, taskId), [api, taskId]);
  const { engine, statePlugin } = useTaskTourEngine({ taskId, isEmpty });

  // Wire the `dispatchTourEvent` bridge to the active engine. Keeps the
  // product-side call sites dispatching through the typed engine bus.
  useEffect(() => {
    if (!engine) return;
    const teardownActionBridge = registerTaskTourActionBridge((name) => engine.emitAction(name));
    const teardownTargetRefreshBridge = registerTaskTourTargetRefreshBridge(() => engine.refreshTarget());
    return () => {
      teardownTargetRefreshBridge();
      teardownActionBridge();
    };
  }, [engine]);

  // Engine init can fail / be mid-mount; render nothing until it's ready. The
  // page renders independently in TaskLayout, so this never blanks the layout.
  if (!engine) return null;
  return (
    <TourProvider tour={engine} navigator={navigator}>
      <TourSidePanel statePlugin={statePlugin} />
      <TaskTourPortal taskId={taskId} />
    </TourProvider>
  );
}

interface TaskTourPortalProps {
  taskId: string;
}

/**
 * Element-anchored overlays portaled to `document.body`. Lives under
 * `<TourProvider>` so the widgets (and the traces prep hook, which calls Query
 * Client hooks) share the engine context.
 */
function TaskTourPortal({ taskId }: TaskTourPortalProps) {
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
      <CertificateWidget />
    </TourHost>
  );
}
