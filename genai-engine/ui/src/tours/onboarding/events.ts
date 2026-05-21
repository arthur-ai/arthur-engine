import mitt from "mitt";

export type OnboardingTourEvents = {
  "onboarding:test": { templateId: string };
  "onboarding:settings-opened": undefined;
};

export const onboardingTourEvents = mitt<OnboardingTourEvents>();
