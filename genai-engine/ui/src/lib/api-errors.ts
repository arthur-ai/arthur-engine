// Shared error-shape predicates for backend responses.
//
// UP-4390 introduced a structured 429 body for the org-token quota gate:
//   { detail: { error_code: "TOKEN_LIMIT_EXCEEDED", message, tokens_limit, tokens_used } }
// Multiple call sites need to detect it without depending on the exact
// transport (axios vs. fetch) or whether the body has been pre-parsed.

import { AxiosError, isAxiosError } from "axios";

export interface TokenLimitExceededDetail {
  error_code: "TOKEN_LIMIT_EXCEEDED";
  message: string;
  tokens_limit?: number | null;
  tokens_used?: number | null;
}

export const TOKEN_LIMIT_EXCEEDED_CODE = "TOKEN_LIMIT_EXCEEDED";

const isTokenLimitDetail = (value: unknown): value is TokenLimitExceededDetail =>
  typeof value === "object" &&
  value !== null &&
  "error_code" in value &&
  (value as { error_code?: unknown }).error_code === TOKEN_LIMIT_EXCEEDED_CODE;

/**
 * Returns true if `err` looks like a 429 TOKEN_LIMIT_EXCEEDED response from
 * the engine, regardless of whether the call used axios (generated client),
 * raw fetch (streaming endpoints), or hand-thrown a parsed Error.
 */
export const isTokenLimitExceededError = (err: unknown): boolean => {
  // Axios path: AxiosError with parsed response body.
  if (isAxiosError(err)) {
    const axErr = err as AxiosError<{ detail?: unknown }>;
    if (axErr.response?.status !== 429) return false;
    return isTokenLimitDetail(axErr.response?.data?.detail);
  }
  // Fetch / hand-thrown path: surface objects/strings carrying detail.
  if (typeof err === "object" && err !== null && "detail" in err) {
    return isTokenLimitDetail((err as { detail?: unknown }).detail);
  }
  return false;
};

/**
 * Extracts the structured detail payload from a 429 error, returning null
 * if the shape doesn't match. Useful when a caller wants to surface the
 * specific `tokens_limit` / `tokens_used` values.
 */
export const getTokenLimitDetail = (err: unknown): TokenLimitExceededDetail | null => {
  if (isAxiosError(err)) {
    const axErr = err as AxiosError<{ detail?: unknown }>;
    const detail = axErr.response?.data?.detail;
    return isTokenLimitDetail(detail) ? detail : null;
  }
  if (typeof err === "object" && err !== null && "detail" in err) {
    const detail = (err as { detail?: unknown }).detail;
    return isTokenLimitDetail(detail) ? detail : null;
  }
  return null;
};
