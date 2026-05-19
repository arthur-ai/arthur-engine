import { useEffect, useRef } from "react";

import type { MajorTaskId, StepId } from "../steps";
import { runMajorTaskExit, runStepAction, useActionRegistry } from "../stores/action-registry.store";

export { runStepAction, runMajorTaskExit };

// Fires when the user clicks Next on this step.
export const useStepAction = (stepId: StepId, action: () => void): void => {
  const actionRef = useRef(action);
  actionRef.current = action;

  useEffect(() => {
    const wrapped = () => actionRef.current();
    return useActionRegistry.getState().registerStep(stepId, wrapped);
  }, [stepId]);
};

// Fires when leaving a major task (final subtask completed or skip-section).
export const useMajorTaskExitAction = (majorTaskId: MajorTaskId, action: () => void): void => {
  const actionRef = useRef(action);
  actionRef.current = action;

  useEffect(() => {
    const wrapped = () => actionRef.current();
    return useActionRegistry.getState().registerMajorTaskExit(majorTaskId, wrapped);
  }, [majorTaskId]);
};
