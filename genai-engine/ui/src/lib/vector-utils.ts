export function extractVectorArray(vector: Record<string, number[] | number[][]> | null | undefined): number[] | null {
  if (!vector || typeof vector !== "object") return null;

  const entries = Object.values(vector);
  if (entries.length === 0) return null;

  let vectorData = entries[0];

  if (Array.isArray(vectorData) && vectorData.length > 0 && Array.isArray(vectorData[0])) {
    vectorData = vectorData[0];
  }

  if (!Array.isArray(vectorData) || vectorData.length === 0) return null;
  if (!vectorData.every((v) => typeof v === "number" && Number.isFinite(v))) return null;

  return vectorData as number[];
}

export function getVectorStats(vector: number[] | null): {
  min: number;
  max: number;
  mean: number;
} | null {
  if (!vector || vector.length === 0) return null;

  let min = Infinity;
  let max = -Infinity;
  let sum = 0;

  for (const value of vector) {
    if (value < min) min = value;
    if (value > max) max = value;
    sum += value;
  }

  const mean = sum / vector.length;

  return { min, max, mean };
}

export function formatVectorPreview(vector: number[] | null, limit: number = 10, decimals: number = 4): string {
  if (!vector || vector.length === 0) return "[]";

  const safeLimit = Math.max(1, Math.min(limit, vector.length));
  const safeDecimals = Math.max(0, Math.min(decimals, 10));

  const preview = vector
    .slice(0, safeLimit)
    .map((v) => (Number.isFinite(v) ? v.toFixed(safeDecimals) : "NaN"))
    .join(", ");

  return vector.length > safeLimit ? `[${preview}, ...]` : `[${preview}]`;
}
