export const TIME_RANGES = {
  "5 minutes": "5 minutes",
  "30 minutes": "30 minutes",
  "1 day": "1 day",
  "1 week": "1 week",
  "1 month": "1 month",
  "3 months": "3 months",
  "1 year": "1 year",
  "all time": "all time",
} as const;
export type TimeRange = (typeof TIME_RANGES)[keyof typeof TIME_RANGES];

export const LEVELS = ["trace", "span", "session", "user"] as const;
export type Level = (typeof LEVELS)[number];

export const DEFAULT_TITLE = "Arthur GenAI Engine";
