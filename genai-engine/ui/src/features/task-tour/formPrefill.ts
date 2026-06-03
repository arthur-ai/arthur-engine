import { useEffect } from "react";

export const TASK_TOUR_FORM_PREFILL_EVENT = "task-tour:form-prefill";

export type TaskTourFormPrefillMode = "replace" | "empty-only";
export type TaskTourFormPrefillValues = Record<string, unknown>;

export interface TaskTourFormPrefill {
  targetId: string;
  value?: string;
  values?: TaskTourFormPrefillValues;
  mode?: TaskTourFormPrefillMode;
}

export function dispatchTaskTourFormPrefill(prefill: TaskTourFormPrefill): void {
  window.dispatchEvent(new CustomEvent<TaskTourFormPrefill>(TASK_TOUR_FORM_PREFILL_EVENT, { detail: prefill }));
}

export function shouldApplyTaskTourFormPrefill(prefill: Pick<TaskTourFormPrefill, "mode">, hasExistingValue: boolean): boolean {
  return prefill.mode !== "empty-only" || !hasExistingValue;
}

export function getTaskTourFormPrefillValue(prefill: TaskTourFormPrefill, key?: string): unknown {
  if (key) return prefill.values?.[key];
  return prefill.value;
}

export function useTaskTourFormPrefill(targetId: string | undefined, onPrefill: (prefill: TaskTourFormPrefill) => void): void {
  useEffect(() => {
    if (!targetId) return;
    const handler = (event: Event) => {
      const prefill = (event as CustomEvent<TaskTourFormPrefill>).detail;
      if (prefill?.targetId !== targetId) return;
      onPrefill(prefill);
    };

    window.addEventListener(TASK_TOUR_FORM_PREFILL_EVENT, handler);
    return () => window.removeEventListener(TASK_TOUR_FORM_PREFILL_EVENT, handler);
  }, [onPrefill, targetId]);
}
