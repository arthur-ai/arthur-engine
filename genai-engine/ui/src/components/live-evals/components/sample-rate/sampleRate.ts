import z from "zod";

// The form holds the rate as a percentage string; "" means every trace.
export const samplePercentSchema = z.string().refine(
  (value) => {
    if (value.trim() === "") return true;
    const percent = Number(value);
    return Number.isFinite(percent) && percent >= 1 && percent <= 100;
  },
  { error: "Enter a percentage from 1 to 100, or leave it empty to evaluate every trace" }
);

export const percentToSampleRate = (percent: string): number | null => (percent.trim() === "" ? null : Number(percent) / 100);

// Rounded to two decimals so 0.333 shows as 33.3, not 33.300000000000004.
export const sampleRateToPercent = (rate: number | null | undefined): string => (rate == null ? "" : String(Math.round(rate * 10000) / 100));
