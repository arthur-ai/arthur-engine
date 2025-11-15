import { NestedSpanWithMetricsResponse } from "@/lib/api-client/api-client";
import { TransformDefinition, Column } from "../form/shared";

// Converts value to string: primitives as-is, objects/arrays via JSON.stringify
function stringifyValue(value: any): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  
  try {
    return JSON.stringify(value);
  } catch (error) {
    return String(value);
  }
}

// Executes transform on spans, returns extracted columns. Uses first match if multiple spans found.
export function executeTransform(
  spans: NestedSpanWithMetricsResponse[],
  transform: TransformDefinition
): Column[] {
  const columns: Column[] = [];

  for (const colDef of transform.columns) {
    const matchingSpans = spans.filter((span) => span.span_name === colDef.span_name);

    if (matchingSpans.length === 0) {
      columns.push({
        name: colDef.column_name,
        value: stringifyValue(colDef.fallback ?? ""),
        path: `${colDef.span_name}.${colDef.attribute_path}`,
        span_name: colDef.span_name,
        attribute_path: colDef.attribute_path,
        matchCount: 0,
      });
    } else {
      const span = matchingSpans[0];
      const value = getNestedValue(span.raw_data, colDef.attribute_path);

      columns.push({
        name: colDef.column_name,
        value: value !== undefined && value !== null 
          ? stringifyValue(value) 
          : stringifyValue(colDef.fallback ?? ""),
        path: `${span.span_name}.${colDef.attribute_path}`,
        span_name: colDef.span_name,
        attribute_path: colDef.attribute_path,
        matchCount: matchingSpans.length,
        selectedSpanId: span.span_id,
        allMatches: matchingSpans.length > 1 ? matchingSpans.map(s => ({
          span_id: s.span_id,
          span_name: s.span_name || "unknown",
          extractedValue: stringifyValue(getNestedValue(s.raw_data, colDef.attribute_path)),
        })) : undefined,
      });
    }
  }

  return columns;
}

// Extracts value from nested object using dot-notation path
function getNestedValue(obj: any, path: string): any {
  if (!obj || !path) return undefined;

  const keys = path.split(".");
  let current = obj;

  for (const key of keys) {
    if (current && key in current) {
      current = current[key];
    } else {
      return undefined;
    }
  }

  return current;
}

