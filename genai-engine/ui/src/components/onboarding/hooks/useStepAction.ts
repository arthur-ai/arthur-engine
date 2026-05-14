import { useEffect, useRef } from "react";

import type { StepId } from "../steps";
import { runStepAction, useActionRegistry } from "../stores/action-registry.store";

export { runStepAction };

// Registers the "Next button" action for a step
export const useStepAction = (stepId: StepId, action: () => void): void => {
  const actionRef = useRef(action);
  actionRef.current = action;

  useEffect(() => {
    const wrapped = () => actionRef.current();
    return useActionRegistry.getState().register(stepId, wrapped);
  }, [stepId]);
};
