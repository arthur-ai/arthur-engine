import { getLocaleForCurrency } from "./currencyLocales";

/**
 * Local implementation so call sites can pass currency code (e.g. from useDisplaySettings).
 * shared-components formatCurrency only accepts (amount); we need (amount, currencyCode).
 */
function getCurrencyFormatter(currency: string): Intl.NumberFormat {
  const code = currency || "USD";
  return new Intl.NumberFormat(getLocaleForCurrency(code), {
    style: "currency",
    currency: code,
    minimumFractionDigits: 6,
    maximumFractionDigits: 6,
  });
}

export function formatCurrency(amount: number, currencyCode: string = "USD"): string {
  const formatter = getCurrencyFormatter(currencyCode);
  const smallThreshold = 0.000001;
  if (amount < smallThreshold) {
    return `< ${formatter.format(smallThreshold)}`;
  }
  return formatter.format(amount);
}

/**
 * Formats the duration between two timestamps in a human-readable format.
 *
 * @param startTime - Start timestamp (UTC string or Date)
 * @param endTime - End timestamp (UTC string or Date)
 * @returns Formatted duration string (e.g., "2h 34m", "5m 42s", "23s") or null if invalid
 */
export function formatTimestampDuration(startTime: string | Date, endTime: string | null | undefined): string | null {
  if (!endTime) return null;

  try {
    const parseDate = (dateInput: string | Date): Date => {
      if (dateInput instanceof Date) return dateInput;
      const dateString = dateInput;
      const isoString = dateString.includes("Z") || dateString.match(/[+-]\d{2}:\d{2}$/) ? dateString : dateString.replace(" ", "T") + "Z";
      return new Date(isoString);
    };

    const start = parseDate(startTime);
    const end = parseDate(endTime);

    if (isNaN(start.getTime()) || isNaN(end.getTime())) return null;

    const durationMs = end.getTime() - start.getTime();
    if (durationMs < 0) return null;

    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      const remainingMinutes = minutes % 60;
      return `${hours}h ${remainingMinutes}m`;
    }
    if (minutes > 0) {
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${seconds}s`;
  } catch {
    return null;
  }
}

/**
 * Normalize various date inputs to a Date instance.
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

/**
 * Format a date/time for display in a specific IANA timezone.
 * Use this for all user-visible timestamps so they respect the selected timezone.
 */
export function formatDateInTimezone(value: string | number | Date | null | undefined, timezone: string): string {
  const date = toDate(value);
  if (!date) return "";
  try {
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      timeZone: timezone,
    }).format(date);
  } catch {
    return "";
  }
}

export { formatDate, formatUTCTimestamp, formatDuration, capitalize, truncateText } from "@arthur/shared-components";
