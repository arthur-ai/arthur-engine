import {
  capitalize,
  DATE_FORMAT_12H_TIMEZONE,
  DATE_FORMAT_24H_TIMEZONE,
  DATE_FORMAT_24H_UTC,
  formatDate,
  formatDurationMs,
  formatTimestampDuration as formatTimestampDurationShared,
  formatUTCTimestamp,
  truncateText,
} from "@arthur/shared-components";

/**
 * Default: formatDate, formatUTCTimestamp, formatDurationMs, formatTimestampDuration, capitalize,
 * truncateText come from @arthur/shared-components; use them when no user timezone or 12/24h
 * preference is needed.
 *
 * Local / extended: formatDateInTimezone(value, timezone, options?) is local; it is intended to be
 * migrated into shared-components later. Format costs with formatCost from @arthur/shared-components.
 */

function toDate(value: string | number | Date | null | undefined): Date | null {
  if (value == null) return null;
  if (value instanceof Date) return value;
  if (typeof value === "number") return new Date(value);
  const str = String(value);
  const isoString = str.includes("Z") || str.match(/[+-]\d{2}:\d{2}$/) ? str : str.replace(" ", "T") + "Z";
  const date = new Date(isoString);
  return isNaN(date.getTime()) ? null : date;
}

export interface FormatDateInTimezoneOptions {
  hour12?: boolean;
}

/** Format a date/time for display in a specific IANA timezone (including UTC). Supports 12/24h. */
export function formatDateInTimezone(
  value: string | number | Date | null | undefined,
  timezone: string,
  options?: FormatDateInTimezoneOptions
): string {
  const date = toDate(value);
  if (!date) return "";
  const hour12 = options?.hour12 ?? false;
  try {
    const formatted = new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12,
      timeZone: timezone,
    }).format(date);
    if (timezone === "UTC") {
      return `${formatted} UTC`;
    }
    return formatted;
  } catch {
    return "";
  }
}

export {
  formatDate,
  formatDurationMs,
  formatUTCTimestamp,
  formatTimestampDurationShared as formatTimestampDuration,
  capitalize,
  truncateText,
  DATE_FORMAT_24H_TIMEZONE,
  DATE_FORMAT_12H_TIMEZONE,
  DATE_FORMAT_24H_UTC,
};
