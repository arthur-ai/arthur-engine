import dayjs from "dayjs";
import duration from "dayjs/plugin/duration";

dayjs.extend(duration);

const { timeZone } = Intl.DateTimeFormat().resolvedOptions();

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "short",
  timeStyle: "long",
  timeZone,
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
  return dayjs.duration(duration).format("HH:mm:ss");
}
