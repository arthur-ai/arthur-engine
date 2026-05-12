export type RadioOption = {
  id: string;
  label: string;
  dot?: string;
  other?: boolean;
};

export type ChipOption = {
  id: string;
  label: string;
  other?: boolean;
  exclusive?: boolean;
};

export const MATURITY_OPTIONS: RadioOption[] = [
  { id: "prod", label: "Running AI in production", dot: "#2563EB" },
  { id: "building", label: "Building toward production — not live yet", dot: "#F59E0B" },
  { id: "evaluating", label: "Evaluating tools / doing early research", dot: "#F97316" },
  { id: "exploring", label: "Just exploring out of curiosity", dot: "#D1D5DB" },
];

export const BRINGS_OPTIONS: RadioOption[] = [
  { id: "first-eval", label: "Evaluating an evals/observability tool for the first time" },
  { id: "switching", label: "Switching from another tool (it wasn't working for us)" },
  { id: "referral", label: "Recommended by a colleague or partner" },
  { id: "event", label: "Saw Arthur at an event or online" },
  { id: "other", label: "Other", other: true },
];

export const COMPETITOR_OPTIONS: ChipOption[] = [
  { id: "langsmith", label: "LangSmith" },
  { id: "langfuse", label: "LangFuse" },
  { id: "braintrust", label: "BrainTrust" },
  { id: "arize", label: "Arize" },
  { id: "other", label: "Other", other: true },
  { id: "none", label: "None — this is my first evals tool", exclusive: true },
];

export const ATTRIBUTION_OPTIONS: ChipOption[] = [
  { id: "search", label: "Google / organic search" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "wom", label: "Word of mouth / colleague" },
  { id: "event", label: "Event or meetup" },
  { id: "blog", label: "Blog or article" },
  { id: "other", label: "Other" },
];
