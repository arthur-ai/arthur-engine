import { describe, expect, it } from "vitest";

import { defineTourConfig, type TourActionName, type TourPreparationKey, type TourQueryHookId, type TourSectionId, type TourStepId } from "../types";

describe("defineTourConfig", () => {
  it("returns the config unchanged while preserving authoring literals", () => {
    const config = defineTourConfig({
      id: "typed-tour",
      sections: [
        {
          id: "intro",
          steps: [
            {
              id: "open",
              target: { kind: "queryHook", hookId: "primary-button" },
              content: "Open",
              prepare: { key: "load-primary" },
              advanceOn: { type: "action", name: "opened" },
            },
          ],
        },
      ],
    });

    type SectionId = TourSectionId<typeof config>;
    type StepId = TourStepId<typeof config>;
    type ActionName = TourActionName<typeof config>;
    type PreparationKey = TourPreparationKey<typeof config>;
    type QueryHookId = TourQueryHookId<typeof config>;

    const sectionId: SectionId = "intro";
    const stepId: StepId = "open";
    const actionName: ActionName = "opened";
    const preparationKey: PreparationKey = "load-primary";
    const queryHookId: QueryHookId = "primary-button";

    expect(config.sections[0].id).toBe(sectionId);
    expect(config.sections[0].steps[0].id).toBe(stepId);
    expect(actionName).toBe("opened");
    expect(preparationKey).toBe("load-primary");
    expect(queryHookId).toBe("primary-button");
  });
});
