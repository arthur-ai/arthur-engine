export type StepIndex = 0 | 1 | 2;
export type StepName = "identity" | "about" | "discovery";

export const STEP_COUNT = 3;

export const STEP_NAMES: readonly StepName[] = ["identity", "about", "discovery"] as const;

export const STEP_LABELS: readonly string[] = ["Who you are", "Your work", "Finding Arthur"] as const;

export const STEP_HEADINGS: readonly { title: string; subtitle: string }[] = [
  { title: "Tell us about you", subtitle: "We'll spin up a demo task scoped just to you." },
  { title: "Where are you with AI?", subtitle: "Helps us tune the demo to where you actually are." },
  { title: "One more thing", subtitle: "How you found us — so we can do more of it." },
] as const;
