import { useCallback, useEffect, useState } from "react";

import { useTracesTourPrep } from "./prep/useTracesTourPrep";
import { registerTaskTourActionBridge } from "./tourActions";
import { useTaskTourEngine } from "./useTaskTourEngine";
import {
  CertificateWidget,
  ChecklistWidget,
  IntroWidget,
  ResumeFabWidget,
  SpotlightWidget,
  TracesTargetWidget,
} from "./widgets";

import {
  TourHost,
  TourProvider,
  useReactRouterNavigator,
  useTourEngine,
} from "@/features/tour";

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
  const { engine, statePlugin } = useTaskTourEngine({ taskId });

  const [fabAnchorRect, setFabAnchorRect] = useState<DOMRect | null>(null);
  const [panelAnchoredToFab, setPanelAnchoredToFab] = useState(false);

  const handleFabAnchorRectChange = useCallback((rect: DOMRect | null) => {
    setFabAnchorRect(rect);
  }, []);

  // Wire the legacy `dispatchTourEvent` shim to the active engine. Keeps the
  // 19 product-side call sites compiling against the v0 import names while
  // routing actions through v1's typed engine bus.
  useEffect(() => {
    if (!engine) return;
    return registerTaskTourActionBridge((name) => engine.emitAction(name));
  }, [engine]);

  // The dock flag is only meaningful while the tour is actively running.
  // Whenever the persisted status leaves `in-progress` — dismissed, completed,
  // skipped, or reset back to unseen — clear the flag so the FAB visibility
  // logic reverts to its default (`dismissed` is the only persisted state
  // that should show the FAB).
  useEffect(() => {
    return statePlugin.store.subscribe((state, prev) => {
      if (prev.snapshot.status === state.snapshot.status) return;
      if (state.snapshot.status !== "in-progress") setPanelAnchoredToFab(false);
    });
  }, [statePlugin]);

  if (!engine) return null;
  return (
    <TourProvider tour={engine} navigator={navigator}>
      <TaskTourBody
        statePlugin={statePlugin}
        workspaceLabel={workspaceLabel}
        taskId={taskId}
        panelAnchoredToFab={panelAnchoredToFab}
        fabAnchorRect={fabAnchorRect}
        onFabAnchorRectChange={handleFabAnchorRectChange}
        onResume={() => setPanelAnchoredToFab(true)}
      />
    </TourProvider>
  );
}

interface TaskTourBodyProps {
  statePlugin: ReturnType<typeof useTaskTourEngine>["statePlugin"];
  workspaceLabel?: string;
  taskId: string;
  panelAnchoredToFab: boolean;
  fabAnchorRect: DOMRect | null;
  onFabAnchorRectChange: (rect: DOMRect | null) => void;
  onResume: () => void;
}

/**
 * Inner shell rendered under `<TourProvider>`. Lives here (rather than in
 * `TaskTour`) so the widgets that need `useTour*` hooks have access to the
 * engine context, and so the prep hook (which calls Query Client hooks) sits
 * inside the same provider tree as the rest of the tour subtree.
 */
function TaskTourBody({
  statePlugin,
  workspaceLabel,
  taskId,
  panelAnchoredToFab,
  fabAnchorRect,
  onFabAnchorRectChange,
  onResume,
}: TaskTourBodyProps) {
  // Register the traces preparation hook (keyed by
  // `TASK_TOUR_PREPARATIONS.traceOpened`). The engine consults this on
  // `prepare: { key }` steps before resolving the spotlight target.
  useTracesTourPrep({ taskId });

  return (
    <TourHost>
      <TracesTargetWidget />
      <IntroWidget />
      <SpotlightWidget />
      <ChecklistWidget statePlugin={statePlugin} panelAnchorRect={panelAnchoredToFab ? fabAnchorRect : null} />
      <ResumeFabWrapper
        statePlugin={statePlugin}
        onAnchorRectChange={onFabAnchorRectChange}
        panelAnchoredToFab={panelAnchoredToFab}
        onResume={onResume}
      />
      <CertificateWidget workspaceLabel={workspaceLabel} />
    </TourHost>
  );
}

interface ResumeFabWrapperProps {
  statePlugin: ReturnType<typeof useTaskTourEngine>["statePlugin"];
  onAnchorRectChange: (rect: DOMRect | null) => void;
  panelAnchoredToFab: boolean;
  onResume: () => void;
}

/**
 * Wraps `ResumeFabWidget` to dock the checklist panel next to the FAB the
 * moment the user resumes from `dismissed`.
 *
 * Listens to `tour:resume` only — NOT `tour:start`. Initial auto-start would
 * otherwise set the dock flag for the whole tour, which would (a) display
 * the FAB during normal running, and (b) keep the FAB visible after
 * completion (since the flag never gets reset), letting a stray click on it
 * loop the engine back to section 0 via `actions.start({ resume: true })`.
 */
function ResumeFabWrapper({ statePlugin, onAnchorRectChange, panelAnchoredToFab, onResume }: ResumeFabWrapperProps) {
  const engine = useTourEngine();

  useEffect(() => {
    const handler = () => onResume();
    engine.on("tour:resume", handler);
    return () => {
      engine.off("tour:resume", handler);
    };
  }, [engine, onResume]);

  return (
    <ResumeFabWidget
      statePlugin={statePlugin}
      onAnchorRectChange={onAnchorRectChange}
      panelAnchoredToFab={panelAnchoredToFab}
    />
  );
}
