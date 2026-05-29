import type { TryItOutSubmission } from "./schema";

export type OnboardingFormVariant = "linear" | "wizard";

export interface TryItOutSubmitMeta {
  formVariant: OnboardingFormVariant;
}

export interface TryItOutFormProps {
  onBack: () => void;
  onSubmit: (data: TryItOutSubmission, meta: TryItOutSubmitMeta) => void | Promise<void>;
}
