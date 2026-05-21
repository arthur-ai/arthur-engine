import mitt from "mitt";

export type OnboardingTourEvents = {
  "onboarding:chatbot-opened": undefined;
  "onboarding:message-sent": { messageLength: number };
  "onboarding:eval-submitted": undefined;
  "onboarding:settings-opened": undefined;
  "onboarding:request-open-first-trace": undefined;
  "onboarding:trace-drawer-opened": { traceId: string };
  "onboarding:feedback-submitted": undefined;
  "onboarding:add-to-dataset-opened": undefined;
  "onboarding:trace-added-to-dataset": { datasetId: string };
  "onboarding:dataset-detail-opened": { datasetId: string };
  "onboarding:prompt-detail-opened": { promptName: string };
  "onboarding:experiment-created": undefined;
};

export const onboardingTourEvents = mitt<OnboardingTourEvents>();
