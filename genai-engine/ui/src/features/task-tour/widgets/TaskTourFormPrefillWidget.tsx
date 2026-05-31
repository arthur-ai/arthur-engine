import { useCallback } from "react";

import { dispatchTaskTourFormPrefill } from "../formPrefill";

import { useTourEngine, useTourEvent } from "@/features/tour";
import type { StepConfig } from "@/features/tour";

function findStep(steps: StepConfig[], stepId: string | undefined): StepConfig | undefined {
  return steps.find((step) => step.id === stepId);
}

function containsDataTourId(element: Element, targetId: string): boolean {
  if (element.getAttribute("data-tour-id") === targetId) return true;
  return Array.from(element.querySelectorAll("[data-tour-id]")).some((candidate) => candidate.getAttribute("data-tour-id") === targetId);
}

function isSelectorTargetForPrefill(step: StepConfig, targetId: string): boolean {
  return step.target.kind === "selector" && step.target.selector === `[data-tour-id="${targetId}"]`;
}

export function TaskTourFormPrefillWidget() {
  const engine = useTourEngine();
  const handleStepEnter = useCallback(
    (event: { sectionId: string; stepId?: string }) => {
      const section = engine.config.sections.find((candidate) => candidate.id === event.sectionId);
      const step = section ? findStep(section.steps, event.stepId) : undefined;
      if (!step?.formPrefill) return;
      dispatchTaskTourFormPrefill(step.formPrefill);
    },
    [engine]
  );
  const handleTargetFound = useCallback(
    (event: { sectionId: string; stepId: string; element: Element }) => {
      const section = engine.config.sections.find((candidate) => candidate.id === event.sectionId);
      const step = section ? findStep(section.steps, event.stepId) : undefined;
      const formPrefill = step?.formPrefill;
      if (!step || !formPrefill) return;
      if (isSelectorTargetForPrefill(step, formPrefill.targetId)) return;
      if (!containsDataTourId(event.element, formPrefill.targetId)) return;
      dispatchTaskTourFormPrefill(formPrefill);
    },
    [engine]
  );

  useTourEvent("step:enter", handleStepEnter);
  useTourEvent("target:found", handleTargetFound);
  return null;
}
