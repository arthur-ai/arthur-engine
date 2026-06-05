import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS, type TourId } from "../selectors";

import { findElementByExactText, useRegisterQueryHook } from "@/features/tour";

export const DEMO_TASK_PROMPT_NAME = "demo_task_prompt";

export function resolveDemoTaskPromptRowTarget(): Element | null {
  return findElementByExactText(DEMO_TASK_PROMPT_NAME, {
    selector: "th, th *, td, td *, [role='cell'], [role='cell'] *, [role='rowheader'], [role='rowheader'] *",
    closestSelector: "tr, [role='row']",
  });
}

export function resolvePromptOpenInPlaygroundTarget(): Element | null {
  return document.querySelector(tourSelector(TOUR_IDS.promptOpenInPlayground)) ?? document.querySelector(tourSelector(TOUR_IDS.promptsFirstRow));
}

export function resolvePlaygroundPromptCardTarget(): Element | null {
  const cards = document.querySelectorAll(tourSelector(TOUR_IDS.playgroundPromptCard));
  if (cards.length > 0) return cards[cards.length - 1];
  return document.querySelector(tourSelector(TOUR_IDS.playgroundAddPrompt));
}

export function resolvePlaygroundSavePromptTarget(): Element | null {
  const cards = document.querySelectorAll(tourSelector(TOUR_IDS.playgroundPromptCard));
  const newestCard = cards[cards.length - 1];
  return (
    newestCard?.querySelector(tourSelector(TOUR_IDS.playgroundSavePrompt)) ?? document.querySelector(tourSelector(TOUR_IDS.playgroundSavePrompt))
  );
}

export function resolvePromptTagsTarget(): Element | null {
  return document.querySelector(tourSelector(TOUR_IDS.promptTagsPopover)) ?? document.querySelector(tourSelector(TOUR_IDS.promptAddTag));
}

export function resolveCreateExperimentEntryTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.promptsExperimentCreateNew)) ??
    document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton))
  );
}

export function resolveCreateExperimentInfoTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentInfoStep)) ?? document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton))
  );
}

/**
 * The four Experiment Info sub-section beats spotlight a block inside the
 * Info step. The block only exists once the modal finishes its loading spinner
 * and renders InfoStep, so each resolver falls back to the whole info-step box
 * and then the modal surface — mirroring resolveCreateExperimentInfoTarget.
 */
function resolveInfoSubSection(subSectionId: TourId): Element | null {
  return (
    document.querySelector(tourSelector(subSectionId)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentInfoStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal))
  );
}

export function resolveCreateExperimentInfoNameTarget(): Element | null {
  return resolveInfoSubSection(TOUR_IDS.createExperimentInfoName);
}

export function resolveCreateExperimentInfoVersionsTarget(): Element | null {
  return resolveInfoSubSection(TOUR_IDS.createExperimentInfoVersions);
}

export function resolveCreateExperimentInfoDatasetTarget(): Element | null {
  return resolveInfoSubSection(TOUR_IDS.createExperimentInfoDataset);
}

export function resolveCreateExperimentInfoEvaluatorsTarget(): Element | null {
  return resolveInfoSubSection(TOUR_IDS.createExperimentInfoEvaluators);
}

export function resolveCreateExperimentPromptMappingsTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentPromptMappingsStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal)) ??
    document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton))
  );
}

// The explainer beats spotlight the mapping list inside each step; fall back to
// the whole step box and then the modal so the highlight is never stranded
// while the step re-renders after a section switch.
export function resolveCreateExperimentPromptMappingsListTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentPromptMappingsList)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentPromptMappingsStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal))
  );
}

export function resolveCreateExperimentEvalMappingsListTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentEvalMappingsList)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentEvalMappingsStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal))
  );
}

export function resolveCreateExperimentFinalTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentEvalMappingsStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentSubmit)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal)) ??
    document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton))
  );
}

export function PromptTargetWidget() {
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.demoTaskPromptRow, resolveDemoTaskPromptRowTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.promptOpenInPlayground, resolvePromptOpenInPlaygroundTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.promptTags, resolvePromptTagsTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.playgroundPromptCard, resolvePlaygroundPromptCardTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.playgroundSavePrompt, resolvePlaygroundSavePromptTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentEntry, resolveCreateExperimentEntryTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentInfo, resolveCreateExperimentInfoTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentInfoName, resolveCreateExperimentInfoNameTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentInfoVersions, resolveCreateExperimentInfoVersionsTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentInfoDataset, resolveCreateExperimentInfoDatasetTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentInfoEvaluators, resolveCreateExperimentInfoEvaluatorsTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings, resolveCreateExperimentPromptMappingsTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappingsList, resolveCreateExperimentPromptMappingsListTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentEvalMappingsList, resolveCreateExperimentEvalMappingsListTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentFinal, resolveCreateExperimentFinalTarget);
  return null;
}
