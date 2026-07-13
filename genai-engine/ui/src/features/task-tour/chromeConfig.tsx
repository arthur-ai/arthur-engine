import type { TourChromeConfig, TourChromeSection } from "@arthur/shared-components/tour";
import { Box, useTheme } from "@mui/material";
import { useMemo } from "react";

import { ADLCFlywheel } from "./components/ADLCFlywheel";
import { TASK_TOUR_SECTIONS, TASK_TOUR_SHORT_NAME, TASK_TOUR_TITLE } from "./data";
import { getTaskTourStepLabel } from "./tour-config";
import { DEFAULT_OCCLUSION_HINT, TASK_TOUR_OCCLUSION_HINTS, TASK_TOUR_TARGET_LOST_HINTS } from "./tourActions";

import { trackDynamic } from "@/services/analytics";

/**
 * Maps the Evals-101 content (`TASK_TOUR_SECTIONS`) into the generic
 * `TourContent` the shared `@arthur/shared-components/tour` chrome renders from.
 * Branded illustrations (the section hero image, the ADLC flywheel) are passed
 * as `ReactNode` slots; the engine/chrome stay content-agnostic.
 *
 * Static (no theme/runtime dependency), so it is built once at module load.
 */
const SECTIONS: TourChromeSection[] = TASK_TOUR_SECTIONS.map((section, index) => ({
  id: section.id,
  title: section.title,
  kicker: section.kicker,
  items: section.items.map((item) => ({ id: item.id, title: item.title })),
  intro: {
    kicker: section.kicker,
    heading: section.intro.heading,
    body: section.intro.body,
    cta: section.intro.cta,
    scenario: section.intro.scenario,
    hero: section.intro.hero ? (
      <Box
        component="img"
        src={section.intro.hero.src}
        alt={section.intro.hero.alt}
        loading="lazy"
        sx={{ display: "block", width: section.intro.hero.width, maxWidth: "100%", height: "auto", borderRadius: 2 }}
      />
    ) : undefined,
    diagram: section.intro.showFlywheel ? <ADLCFlywheel /> : undefined,
    // The emphasized gradient "hero" layout: the opening section + any section
    // that opts into the flywheel (mirrors the pre-extraction SectionIntroDialog).
    emphasize: index === 0 || section.intro.showFlywheel === true,
  },
}));

/**
 * The `TourChromeProvider` config for the task tour. Reads the docked-panel
 * layout tokens from the `theme.tour` augmentation so the look matches exactly,
 * and wires arthur-engine's analytics sink + the Evals-101 hint copy. `itemKey`
 * is omitted — the package default (`${sectionId}.${itemId}`) already matches
 * the engine's persistence `getKey`.
 */
export function useTaskTourChromeConfig(): TourChromeConfig {
  const { tour } = useTheme();
  return useMemo<TourChromeConfig>(
    () => ({
      title: TASK_TOUR_TITLE,
      shortName: TASK_TOUR_SHORT_NAME,
      sections: SECTIONS,
      targetLostHints: TASK_TOUR_TARGET_LOST_HINTS,
      occlusionHints: TASK_TOUR_OCCLUSION_HINTS,
      defaultOcclusionHint: DEFAULT_OCCLUSION_HINT,
      resolveStepLabel: getTaskTourStepLabel,
      hintColor: tour.hintColor,
      railWidth: tour.railWidth,
      contentWidth: tour.contentWidth,
      track: trackDynamic,
    }),
    [tour.hintColor, tour.railWidth, tour.contentWidth]
  );
}
