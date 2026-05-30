import { TASK_TOUR_QUERY_HOOKS } from "../content/wiring";
import { tourSelector, TOUR_IDS } from "../selectors";

import { findElementByExactText, useRegisterQueryHook } from "@/features/tour";

const DEMO_TASK_PROMPT_NAME = "demo_task_prompt";

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
  return newestCard?.querySelector(tourSelector(TOUR_IDS.playgroundSavePrompt)) ?? document.querySelector(tourSelector(TOUR_IDS.playgroundSavePrompt));
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

export function resolveCreateExperimentPromptMappingsTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentPromptMappingsStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal)) ??
    document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton))
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
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings, resolveCreateExperimentPromptMappingsTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentFinal, resolveCreateExperimentFinalTarget);
  return null;
}
