import dayjs from "dayjs";
import duration from "dayjs/plugin/duration";

dayjs.extend(duration);

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "short",
  timeStyle: "long",
  timeZone: "UTC",
});

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 5,
  maximumFractionDigits: 5,
});

export function formatDate(date: string | Date) {
  return dateFormatter.format(new Date(date));
}

/**
 * Formats a UTC timestamp string (without timezone suffix) to local time with timezone display.
 * Assumes the input string is in UTC if no timezone is specified.
 *
 * @param dateString - UTC timestamp string (e.g., "2024-01-15 10:30:00" or "2024-01-15T10:30:00")
 * @returns Formatted date string in local timezone or "-" if invalid/null
 */
export function formatUTCTimestamp(dateString: string | null | undefined): string {
  if (!dateString) return "-";

  try {
    // If the timestamp doesn't have a 'Z' or timezone offset, append 'Z' to treat it as UTC
    let isoString = dateString;
    if (!dateString.endsWith('Z') && !dateString.match(/[+-]\d{2}:\d{2}$/)) {
      // Replace space with 'T' if needed and add 'Z'
      isoString = dateString.replace(' ', 'T') + 'Z';
    }

    const date = new Date(isoString);
    if (isNaN(date.getTime())) {
      return dateString;
    }

    // Format with timezone name
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZoneName: "short",
    });
  } catch {
    return dateString;
  }
}

export function formatCurrency(amount: number) {
  if (amount < 0.00001) return `< ${currencyFormatter.format(0.00001)}`;
  return currencyFormatter.format(amount);
}

export function formatDuration(duration: number) {
  return dayjs
    .duration(+duration.toPrecision(3), "millisecond")
    .format("H[h] M[m] s[s] SSS[ms]")
    .replace(/\b0[hmst]\b/g, "");
}

/**
 * Formats the duration between two timestamps in a human-readable format.
 *
 * @param startTime - Start timestamp (UTC string or Date)
 * @param endTime - End timestamp (UTC string or Date)
 * @returns Formatted duration string (e.g., "2h 34m", "5m 42s", "23s") or null if invalid
 */
export function formatTimestampDuration(
  startTime: string | Date,
  endTime: string | null | undefined
): string | null {
  if (!endTime) return null;

  try {
    // Parse timestamps as UTC
    const parseDate = (dateInput: string | Date): Date => {
      if (dateInput instanceof Date) return dateInput;
      const dateString = dateInput;
      const isoString = dateString.includes('Z') || dateString.match(/[+-]\d{2}:\d{2}$/)
        ? dateString
        : dateString.replace(' ', 'T') + 'Z';
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
    } else if (minutes > 0) {
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      return `${seconds}s`;
    }
  } catch {
    return null;
  }
}
