import { getNestedValue } from "@arthur/shared-components";

export {
  getNestedValue,
  getSpanInput,
  getSpanOutput,
  getSpanInputMimeType,
  getSpanDuration,
  flattenSpans,
  getSpanModel,
  getSpanType,
  getSpanIcon,
  isSpanOfType,
} from "@arthur/shared-components";

/**
 * Like getNestedValue but supports '*' as a wildcard segment.
 * When '*' is encountered on an array, iterates all items.
 * When '*' is encountered on an object, iterates all values.
 * Returns a flat array of all matched leaf values, or undefined if none found.
 */
export function getNestedValueWildcard<Return>(obj: unknown, path: string): Return[] | undefined {
  if (!path.includes("*")) {
    const result = getNestedValue<Return>(obj, path);
    return result !== undefined ? [result] : undefined;
  }

  if (typeof obj !== "object" || obj === null) return undefined;

  const keys = path.split(".");
  const results = collectWildcard(obj, keys, 0);
  return results.length > 0 ? (results as Return[]) : undefined;
}

function collectWildcard(current: unknown, keys: string[], index: number): unknown[] {
  if (index === keys.length) {
    return current != null ? [current] : [];
  }

  const key = keys[index];

  if (key === "*") {
    let items: unknown[];
    if (Array.isArray(current)) {
      items = current;
    } else if (typeof current === "object" && current !== null) {
      items = Object.values(current);
    } else {
      return [];
    }

    const results: unknown[] = [];
    for (const item of items) {
      results.push(...collectWildcard(item, keys, index + 1));
    }
    return results;
  }

  if (current == null) return [];

  const numIndex = Number(key);
  if (!Number.isNaN(numIndex) && Array.isArray(current)) {
    return collectWildcard(current[numIndex], keys, index + 1);
  }

  if (typeof current === "object" && key in current) {
    return collectWildcard((current as Record<string, unknown>)[key], keys, index + 1);
  }

  return [];
}
