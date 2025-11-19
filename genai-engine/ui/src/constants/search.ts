export const SCORE_THRESHOLDS = {
  nearText: {
    good: 0.3,
    medium: 0.6,
  },
  bm25: {
    good: 0.7,
    medium: 0.4,
  },
} as const;

export const DEFAULT_SEARCH_SETTINGS = {
  limit: 10,
  distance: 0.7,
  alpha: 0.5,
  includeMetadata: true,
  includeVector: false,
} as const;
