import { CELL_TRUNCATION_LENGTH } from "@/constants/datasetConstants";

export function formatCellValue(
  value: unknown,
  maxLength: number = CELL_TRUNCATION_LENGTH
): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "✓" : "✗";
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "string" && value.length > maxLength) {
    return value.substring(0, maxLength) + "...";
  }
  return String(value);
}

export function formatFullValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}
