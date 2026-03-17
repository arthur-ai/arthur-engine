import type { TimezoneOption } from "./types";

/**
 * Default list of common IANA timezones with human-readable labels.
 * Used when timezoneOptions is not provided. Kept static for portability
 * across environments (no Intl.supportedValuesOf dependency).
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
  { value: "Asia/Kolkata", label: "India (Asia/Kolkata)" },
  { value: "Asia/Shanghai", label: "China (Asia/Shanghai)" },
  { value: "Asia/Tokyo", label: "Japan (Asia/Tokyo)" },
  { value: "Australia/Sydney", label: "Eastern Australia (Australia/Sydney)" },
  { value: "Australia/Melbourne", label: "Eastern Australia (Australia/Melbourne)" },
  { value: "Pacific/Auckland", label: "New Zealand (Pacific/Auckland)" },
  { value: "America/Sao_Paulo", label: "Brasília (America/Sao_Paulo)" },
  { value: "America/Buenos_Aires", label: "Argentina (America/Buenos_Aires)" },
];
