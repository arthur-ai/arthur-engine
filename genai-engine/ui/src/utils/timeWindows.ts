/**
 * Time Window and Bucketing Utility
 *
 * This module provides canonical time window calculations for dashboard metrics.
 * All boundaries are inclusive start, exclusive end to avoid double-counting.
 *
 * Timezone handling: Uses browser's local timezone for all calendar boundaries.
 * DST handling: All calculations use timezone-aware date operations.
 */

export type TimeInterval = "hour" | "day" | "week" | "mtd" | "ytd" | "year";
export type BucketSize = "minute" | "5min" | "hour" | "day" | "week" | "month";

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
  xLabelFormat: "time" | "date" | "month";
  /** Suggested number of data points for optimal visualization */
  suggestedPoints: number;
  /** Tick step for X-axis (show every Nth label) */
  tickStep: number;
}

/**
 * Configuration options for time window calculation
 */
export interface TimeWindowConfig {
  /** First day of week (0 = Sunday, 1 = Monday). Default: 1 (Monday) */
  firstDayOfWeek?: 0 | 1;
  /** Timezone (currently uses browser local timezone) */
  timezone?: string;
}

/**
 * Get the start of the current hour in local timezone
 */
function getStartOfHour(now: Date): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), 0, 0, 0);
}

/**
 * Get the start of the current day (midnight) in local timezone
 */
function getStartOfDay(now: Date): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
}

/**
 * Get the start of the current calendar week in local timezone
 * @param firstDayOfWeek 0 = Sunday, 1 = Monday
 */
function getStartOfWeek(now: Date, firstDayOfWeek: 0 | 1 = 1): Date {
  const dayOfWeek = now.getDay(); // 0 = Sunday, 6 = Saturday
  const diff = (dayOfWeek - firstDayOfWeek + 7) % 7;
  const weekStart = new Date(now);
  weekStart.setDate(now.getDate() - diff);
  return getStartOfDay(weekStart);
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
 * - hour: Last 60 minutes up to now
 * - day: Midnight of current day to now
 * - week: Start of current calendar week to now
 * - mtd: 1st of current month to now (Month-To-Date)
 * - ytd: January 1st of current year to now (Year-To-Date)
 * - year: Last 12 months to now (rolling 12 months)
 *
 * @example
 * ```typescript
 * const window = getTimeWindowAndBucketing("day");
 * // { start: 2026-02-06T00:00:00, end: 2026-02-06T17:30:00, bucketSize: "hour", ... }
 * ```
 */
export function getTimeWindowAndBucketing(
  interval: TimeInterval,
  now: Date = new Date(),
  config: TimeWindowConfig = {}
): TimeWindow {
  const { firstDayOfWeek = 1 } = config;

  switch (interval) {
    case "hour": {
      // Last 60 minutes up to now
      const start = new Date(now.getTime() - 60 * 60 * 1000);
      return {
        start,
        end: now,
        bucketSize: "minute",
        bucketMs: 60 * 1000,
        xLabelFormat: "time",
        suggestedPoints: 60,
        tickStep: 10, // Show every 10th minute
      };
    }

    case "day": {
      // From midnight to now
      const start = getStartOfDay(now);
      const bucketMs = 60 * 60 * 1000;

      // Calculate actual number of hours from midnight to now
      const durationMs = now.getTime() - start.getTime();
      const suggestedPoints = Math.ceil(durationMs / bucketMs);

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
      // From start of calendar week to now
      const start = getStartOfWeek(now, firstDayOfWeek);
      const bucketMs = 24 * 60 * 60 * 1000;

      // Calculate actual number of days from week start to now
      const durationMs = now.getTime() - start.getTime();
      const suggestedPoints = Math.ceil(durationMs / bucketMs);

      return {
        start,
        end: now,
        bucketSize: "day",
        bucketMs,
        xLabelFormat: "date",
        suggestedPoints,
        tickStep: 1, // Show all days (max 7)
      };
    }

    case "mtd": {
      // From 1st of month to now (Month-To-Date)
      const start = getStartOfMonth(now);
      const bucketMs = 24 * 60 * 60 * 1000;

      // Calculate actual number of days from 1st to now
      const durationMs = now.getTime() - start.getTime();
      const suggestedPoints = Math.ceil(durationMs / bucketMs);

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
      const suggestedPoints = Math.ceil(durationMs / bucketMs);

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

    case "year": {
      // Last 12 months to now (rolling 12 months)
      const start = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
      return {
        start,
        end: now,
        bucketSize: "month",
        bucketMs: 30 * 24 * 60 * 60 * 1000, // Approximate
        xLabelFormat: "month",
        suggestedPoints: 12,
        tickStep: 1, // Show all months
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
    hour: "Hour",
    day: "Day",
    week: "Week",
    mtd: "Month",
    ytd: "YTD",
    year: "Year",
  };
  return labels[interval];
}

/**
 * Get display label for time aggregation context
 */
export function getTimeRangeDescription(interval: TimeInterval): string {
  const descriptions: Record<TimeInterval, string> = {
    hour: "this hour",
    day: "today",
    week: "this week",
    mtd: "this month",
    ytd: "year to date",
    year: "this year",
  };
  return descriptions[interval];
}
