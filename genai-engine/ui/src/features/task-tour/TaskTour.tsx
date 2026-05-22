import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CertificateDialog } from "./components/CertificateDialog";
import { ChecklistTour } from "./components/ChecklistTour";
import { ResumeFab } from "./components/ResumeFab";
import { buildTourConfig } from "./tour-config";
import { TASK_TOUR_STORAGE_KEY, useTaskTourPersistence } from "./useTaskTourPersistence";

import { createAnalyticsPlugin, createPersistencePlugin, createTour, TourProvider, useReactRouterNavigator, type TourEngine } from "@/features/tour";
import { track } from "@/services/amplitude";

export interface TaskTourProps {
  /** Required: the task the tour should bind its routes against. */
  taskId: string;
  /** Optional human-readable name displayed on the completion certificate. */
  workspaceLabel?: string;
}

/**
 * Top-level mount for the Evals 101 / ADLC tour. Owns the engine lifecycle,
 * binds it to React Router via `useReactRouterNavigator`, and drives the
 * persistence-aware auto-show / resume / hide behaviour:
 *
 * - `unseen`        → auto-start once on first mount; user sees Section 1 intro
 * - `in-progress`   → render the panel + spotlight; persistence is held until
 *                     the engine terminates
 * - `dismissed`     → render only the floating `ResumeFab`
 * - `completed`     → render nothing (and unmount the FAB)
 *
 * Engine is memoized on `taskId` because section/step routes embed it. When
 * the user moves to a different task we destroy the previous engine and
 * create a fresh one (see Phase 2 handoff §7.2).
 */
export function TaskTour({ taskId, workspaceLabel }: TaskTourProps) {
  const navigator = useReactRouterNavigator();

  // Build (and tear down) the engine per task.
  const engine = useMemo<TourEngine>(() => {
    return createTour({
      config: buildTourConfig(taskId),
      plugins: [createAnalyticsPlugin({ track, prefix: "task-tour" }), createPersistencePlugin({ storageKey: TASK_TOUR_STORAGE_KEY })],
    });
  }, [taskId]);

  useEffect(() => () => engine.destroy(), [engine]);

  const { status, setStatus } = useTaskTourPersistence();

  // Auto-start once per `unseen` status. We use a ref to gate so that the
  // start side-effect doesn't re-fire if `status` flickers (e.g. the
  // persistence plugin writes `in-progress` synchronously inside `start()`,
  // which would re-render with a new status before this effect has settled).
  const autoStartedRef = useRef(false);
  useEffect(() => {
    if (autoStartedRef.current) return;
    if (status !== "unseen") return;
    if (engine.getState().status !== "idle") return;
    autoStartedRef.current = true;
    engine.start();
  }, [engine, status]);

  const [certificateOpen, setCertificateOpen] = useState(false);

  const handleComplete = useCallback(() => {
    setCertificateOpen(true);
    setStatus("completed");
  }, [setStatus]);

  const handleDismiss = useCallback(() => {
    setStatus("dismissed");
  }, [setStatus]);

  const handleResume = useCallback(() => {
    setStatus("in-progress");
    // If the engine is paused, resume picks up at the same step; otherwise
    // (e.g. status was "dismissed" coming from a previous browser session and
    // the engine is freshly idle) start from the beginning.
    const engineState = engine.getState();
    if (engineState.status === "paused") {
      engine.resume();
    } else if (engineState.status === "idle") {
      engine.start();
    } else if (engineState.status === "completed" || engineState.status === "skipped") {
      // The engine is terminal — `start()` will re-initialise it cleanly.
      engine.start();
    }
  }, [engine, setStatus]);

  const handleCertificateClose = useCallback(() => {
    setCertificateOpen(false);
  }, []);

  // `completed` state with the certificate already closed → render nothing.
  if (status === "completed" && !certificateOpen) {
    return null;
  }

  const checklistEnabled = status === "unseen" || status === "in-progress";

  return (
    <TourProvider tour={engine} navigator={navigator}>
      <ChecklistTour enabled={checklistEnabled} onDismiss={handleDismiss} onComplete={handleComplete} />
      {/* Dismissed state: render the resume FAB independently of the engine's
          internal status, because the dismissed status may persist across page
          reloads when the engine is freshly created in the `idle` state. */}
      {!checklistEnabled && !certificateOpen ? <ResumeFab onClick={handleResume} /> : null}

      <CertificateDialog open={certificateOpen} workspaceLabel={workspaceLabel} onClose={handleCertificateClose} />
    </TourProvider>
  );
}
