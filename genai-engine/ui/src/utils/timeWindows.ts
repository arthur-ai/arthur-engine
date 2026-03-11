/**
 * Time Window and Bucketing Utility
 *
 * This module provides canonical time window calculations for dashboard metrics.
 * All boundaries are inclusive start, exclusive end to avoid double-counting.
 *
 * Timezone handling: Uses browser's local timezone for all calendar boundaries.
 * DST handling: All calculations use timezone-aware date operations.
 */

export type TimeInterval = "day" | "week" | "mtd" | "ytd";
export type BucketSize = "hour" | "day" | "week";

export interface TimeWindow {
  /** Inclusive start boundary */
  start: Date;
  /** Exclusive end boundary (typically "now") */
  end: Date;
  /** Bucket size for data aggregation */
  bucketSize: BucketSize;
  /** Bucket size in milliseconds */
  bucketMs: number;
  /** Format string for X-axis labels */
  xLabelFormat: "time" | "date";
  /** Suggested number of data points for optimal visualization */
  suggestedPoints: number;
  /** Tick step for X-axis (show every Nth label) */
  tickStep: number;
}

/**
 * Configuration options for time window calculation
 */
export interface TimeWindowConfig {
  /** Timezone (currently uses browser local timezone) */
  timezone?: string;
}

/**
 * Get the start of the current day (midnight) in local timezone
 */
function getStartOfDay(now: Date): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
}

/**
 * Get the start of the current month in local timezone
 */
function getStartOfMonth(now: Date): Date {
  return new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
}

/**
 * Get the start of the current year in local timezone
 */
function getStartOfYear(now: Date): Date {
  return new Date(now.getFullYear(), 0, 1, 0, 0, 0, 0);
}

/**
 * Calculate time window and bucketing parameters for a given interval
 *
 * @param interval The time interval to calculate
 * @param now Current time (default: new Date())
 * @param config Optional configuration
 * @returns TimeWindow with start, end, bucketing, and formatting info
 *
 * Time interval definitions:
 * - day: Midnight of current day to now
 * - week: Last 7 days up to now
 * - mtd: 1st of current month to now (Month-To-Date)
 * - ytd: January 1st of current year to now (Year-To-Date)
 *
 * @example
 * ```typescript
 * const window = getTimeWindowAndBucketing("day");
 * // { start: 2026-02-06T00:00:00, end: 2026-02-06T17:30:00, bucketSize: "hour", ... }
 * ```
 */
export function getTimeWindowAndBucketing(interval: TimeInterval, now: Date = new Date(), config: TimeWindowConfig = {}): TimeWindow {
  switch (interval) {
    case "day": {
      // From midnight to now
      const start = getStartOfDay(now);
      const bucketMs = 60 * 60 * 1000;

      // Calculate actual number of hours from midnight to now
      const durationMs = now.getTime() - start.getTime();
      const suggestedPoints = Math.max(1, Math.ceil(durationMs / bucketMs));

      // Adjust tick step to show ~8 labels max
      const tickStep = Math.max(1, Math.ceil(suggestedPoints / 8));

      return {
        start,
        end: now,
        bucketSize: "hour",
        bucketMs,
        xLabelFormat: "time",
        suggestedPoints,
        tickStep,
      };
    }

    case "week": {
      // Last 7 days up to now
      const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      const bucketMs = 24 * 60 * 60 * 1000;

      return {
        start,
        end: now,
        bucketSize: "day",
        bucketMs,
        xLabelFormat: "date",
        suggestedPoints: 7,
        tickStep: 1, // Show all days
      };
    }

    case "mtd": {
      // From 1st of month to now (Month-To-Date)
      const start = getStartOfMonth(now);
      const bucketMs = 24 * 60 * 60 * 1000;

      // Calculate actual number of days from 1st to now
      const durationMs = now.getTime() - start.getTime();
      const suggestedPoints = Math.max(1, Math.ceil(durationMs / bucketMs));

      // Adjust tick step to show ~10 labels max
      const tickStep = Math.max(1, Math.ceil(suggestedPoints / 10));

      return {
        start,
        end: now,
        bucketSize: "day",
        bucketMs,
        xLabelFormat: "date",
        suggestedPoints,
        tickStep,
      };
    }

    case "ytd": {
      // From Jan 1st to now (Year-To-Date)
      const start = getStartOfYear(now);
      const bucketMs = 7 * 24 * 60 * 60 * 1000;

      // Calculate actual number of weeks from Jan 1 to now
      const durationMs = now.getTime() - start.getTime();
      const suggestedPoints = Math.max(1, Math.ceil(durationMs / bucketMs));

      // Adjust tick step to show ~13 labels max
      const tickStep = Math.max(1, Math.ceil(suggestedPoints / 13));

      return {
        start,
        end: now,
        bucketSize: "week",
        bucketMs,
        xLabelFormat: "date",
        suggestedPoints,
        tickStep,
      };
    }

    default: {
      const exhaustiveCheck: never = interval;
      throw new Error(`Unhandled interval: ${exhaustiveCheck}`);
    }
  }
}

/**
 * Calculate the number of buckets between start and end
 */
export function calculateBucketCount(start: Date, end: Date, bucketMs: number): number {
  const durationMs = end.getTime() - start.getTime();
  return Math.ceil(durationMs / bucketMs);
}

/**
 * Get display label for an interval
 */
export function getIntervalLabel(interval: TimeInterval): string {
  const labels: Record<TimeInterval, string> = {
    day: "Day",
    week: "7 Days",
    mtd: "Month",
    ytd: "YTD",
  };
  return labels[interval];
}

/**
 * Get display label for time aggregation context
 */
export function getTimeRangeDescription(interval: TimeInterval): string {
  const descriptions: Record<TimeInterval, string> = {
    day: "today",
    week: "last 7 days",
    mtd: "this month",
    ytd: "year to date",
  };
  return descriptions[interval];
}
