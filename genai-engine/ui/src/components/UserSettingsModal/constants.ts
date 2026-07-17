import type { TimezoneOption } from "./types";

/**
 * Default list of common IANA timezones with human-readable labels.
 * Used when timezoneOptions is not provided.
 *
 * This list is intentionally hand-maintained instead of being generated from
 * `Intl.supportedValuesOf("timeZone")`, for a few reasons:
 *
 * - Runtime portability: this UI is a browser SPA, so timezone enumeration
 *   would run in the customer's browser. `Intl.supportedValuesOf` is an ES2022
 *   API (Chrome 99+, Firefox 93+, Safari 15.4+, Node 18+). Self-hosted / on-prem
 *   deployments are frequently accessed from older, locked-down, or air-gapped
 *   browsers where that API may be missing, which would throw and leave the
 *   timezone dropdown empty. A static array renders identically everywhere.
 *   (Note: the TypeScript ES2022 `target` does not polyfill this at runtime.)
 * - Test/CI determinism: Node built with `small-icu` and jsdom can return
 *   trimmed or varying results from `supportedValuesOf`, making tests flaky.
 * - UX: a curated ~30-entry list with friendly labels is far more usable than
 *   the 400+ raw IANA identifiers the runtime would return.
 *
 * Trade-off: supporting a new zone requires a manual edit here. Values are IANA
 * identifiers passed directly to `Intl.DateTimeFormat` (see `formatDateInTimezone`
 * in `src/utils/formatters.ts`), so any valid identifier works without extra config.
 */
export const DEFAULT_TIMEZONE_OPTIONS: TimezoneOption[] = [
  { value: "UTC", label: "UTC" },
  { value: "America/New_York", label: "Eastern (America/New_York)" },
  { value: "America/Chicago", label: "Central (America/Chicago)" },
  { value: "America/Denver", label: "Mountain (America/Denver)" },
  { value: "America/Los_Angeles", label: "Pacific (America/Los_Angeles)" },
  { value: "America/Anchorage", label: "Alaska (America/Anchorage)" },
  { value: "Pacific/Honolulu", label: "Hawaii (Pacific/Honolulu)" },
  { value: "America/Toronto", label: "Eastern – Toronto (America/Toronto)" },
  { value: "America/Vancouver", label: "Pacific – Vancouver (America/Vancouver)" },
  { value: "Europe/London", label: "GMT/BST (Europe/London)" },
  { value: "Europe/Paris", label: "Central European (Europe/Paris)" },
  { value: "Europe/Berlin", label: "Central European (Europe/Berlin)" },
  { value: "Europe/Amsterdam", label: "Central European (Europe/Amsterdam)" },
  { value: "Europe/Moscow", label: "Moscow (Europe/Moscow)" },
  { value: "Asia/Dubai", label: "Gulf (Asia/Dubai)" },
  { value: "Asia/Muscat", label: "Gulf - Oman (Asia/Muscat)" },
  { value: "Asia/Riyadh", label: "Arabia (Asia/Riyadh)" },
  { value: "Asia/Qatar", label: "Arabia - Qatar (Asia/Qatar)" },
  { value: "Asia/Kuwait", label: "Arabia - Kuwait (Asia/Kuwait)" },
  { value: "Asia/Bahrain", label: "Arabia - Bahrain (Asia/Bahrain)" },
  { value: "Asia/Kolkata", label: "India (Asia/Kolkata)" },
  { value: "Asia/Shanghai", label: "China (Asia/Shanghai)" },
  { value: "Asia/Tokyo", label: "Japan (Asia/Tokyo)" },
  { value: "Australia/Lord_Howe", label: "Lord Howe Island (Australia/Lord_Howe)" },
  { value: "Australia/Sydney", label: "Eastern Australia (Australia/Sydney)" },
  { value: "Australia/Melbourne", label: "Eastern Australia (Australia/Melbourne)" },
  { value: "Australia/Hobart", label: "Eastern Australia - Tasmania (Australia/Hobart)" },
  { value: "Australia/Brisbane", label: "Eastern Australia - Brisbane (Australia/Brisbane)" },
  { value: "Australia/Lindeman", label: "Eastern Australia - Lindeman (Australia/Lindeman)" },
  { value: "Australia/Adelaide", label: "Central Australia (Australia/Adelaide)" },
  { value: "Australia/Broken_Hill", label: "Central Australia - Broken Hill (Australia/Broken_Hill)" },
  { value: "Australia/Darwin", label: "Central Australia - Darwin (Australia/Darwin)" },
  { value: "Australia/Eucla", label: "Central Western Australia - Eucla (Australia/Eucla)" },
  { value: "Australia/Perth", label: "Western Australia (Australia/Perth)" },
  { value: "Pacific/Auckland", label: "New Zealand (Pacific/Auckland)" },
  { value: "America/Sao_Paulo", label: "Brasília (America/Sao_Paulo)" },
  { value: "America/Buenos_Aires", label: "Argentina (America/Buenos_Aires)" },
];
