import {
  GuidedStepPopover,
  IntroWidget,
  OcclusionRecoveryWidget,
  ScrollTargetIntoViewWidget,
  SectionCompleteWidget,
  SpotlightWidget,
  TourChromeProvider,
  TourHost,
  TourProvider,
  TourSidePanel,
} from "@arthur/shared-components/tour";
import { useReactRouterNavigator } from "@arthur/shared-components/tour/react-router";
import { useCallback, useEffect, useMemo } from "react";

import { useTaskTourChromeConfig } from "./chromeConfig";
import { createTaskTourEmptyStatePredicate } from "./emptyState";
import { useDetailRouteTourPrep } from "./prep/useDetailRouteTourPrep";
import { useTracesTourPrep } from "./prep/useTracesTourPrep";
import { registerTaskTourActionBridge, registerTaskTourTargetRefreshBridge } from "./tourActions";
import { useTaskTourEngine } from "./useTaskTourEngine";
import {
  CertificateWidget,
  DatasetTargetWidget,
  EvaluateTargetWidget,
  PromptTargetWidget,
  TaskTourFormPrefillWidget,
  TracesTargetWidget,
  TracesTourCleanupWidget,
} from "./widgets";

import { useApi } from "@/hooks/useApi";
import { trackDynamic } from "@/services/analytics";

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
  const chromeConfig = useTaskTourChromeConfig();

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
    <TourChromeProvider value={chromeConfig}>
      <TourProvider tour={engine} navigator={navigator}>
        <TourSidePanel statePlugin={statePlugin} />
        <TaskTourPortal taskId={taskId} />
      </TourProvider>
    </TourChromeProvider>
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
  // Register the dynamic detail-route prep hooks (evaluator / dataset / prompt
  // detail), so those steps navigate to their data-dependent URL when entered
  // out of order instead of stranding on the wrong page.
  useDetailRouteTourPrep({ taskId });

  // Preserve the pre-extraction analytics event names: the shared
  // OcclusionRecoveryWidget emits unprefixed outcomes; re-apply the `task-tour.`
  // prefix the in-tree widget used.
  const trackOcclusion = useCallback((name: string, props?: Record<string, unknown>) => trackDynamic(`task-tour.${name}`, props), []);

  return (
    <TourHost>
      <DatasetTargetWidget />
      <EvaluateTargetWidget />
      <PromptTargetWidget />
      <TracesTargetWidget />
      <TracesTourCleanupWidget />
      <OcclusionRecoveryWidget track={trackOcclusion} />
      <ScrollTargetIntoViewWidget />
      <TaskTourFormPrefillWidget />
      <IntroWidget />
      <SectionCompleteWidget />
      <SpotlightWidget />
      <GuidedStepPopover insetRight="--app-inset-right" />
      <CertificateWidget />
    </TourHost>
  );
}
