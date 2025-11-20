export const buildThresholdsFromSample = (durations: number[]) => {
  const sorted = [...durations].sort((a, b) => a - b);

  const p50 = percentile(sorted, 0.5);
  const p90 = percentile(sorted, 0.9);

  return { p50, p90 };
};

export type Thresholds = ReturnType<typeof buildThresholdsFromSample>;

const percentile = (sorted: number[], p: number) => {
  if (!sorted.length) return 0;
  const idx = Math.floor(p * (sorted.length - 1));
  return sorted[idx];
};

export type Bucket = "ok" | "warning" | "bad";

export const makeBucketer = (p50: number, p90: number) => {
  return (durationMs: number): Bucket => {
    if (durationMs <= p50) return "ok";
    if (durationMs <= p90) return "warning";
    return "bad";
  };
};

export type Bucketer = ReturnType<typeof makeBucketer>;

const ONE_SECOND = 1000;
const ONE_MINUTE = 60 * ONE_SECOND;

export const defaultBucketer: Bucketer = makeBucketer(30 * ONE_SECOND, ONE_MINUTE);
