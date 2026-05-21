import { Tour } from "../types";

import { OnboardingTourEvents } from "./events";

export const onboardingTour: Tour<OnboardingTourEvents> = {
  id: "onboarding",
  sections: [
    {
      id: "welcome",
      title: "Welcome",
      steps: [
        {
          type: "popover",
          id: "welcome",
          route: "/",
          selector: "[data-tour-id='onboarding-welcome']",
          title: "Welcome to Arthur",
          description: "This short tour highlights key areas of the tasks home page.",
        },
      ],
    },
    {
      id: "settings",
      title: "Settings",
      steps: [
        {
          type: "popover",
          id: "settings",
          route: "/",
          selector: "[data-tour-id='onboarding-settings']",
          title: "Settings",
          description: "Open settings to manage your workspace preferences and restart this tour anytime.",
        },
      ],
    },
  ],
};
