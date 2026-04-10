import { useMemo, useState } from "react";

import { getNestedValue, getNestedValueWildcard } from "../../../utils/spans";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

const isPrimitive = (value: unknown): value is string | number | boolean | null | undefined => {
  return typeof value !== "object" || value === null;
};

/**
 * Walk through navigation keys one at a time, treating '*' as "peek at first element"
 */
function resolveNavigationData(rawData: unknown, keys: string[]): { data: unknown; isArray: boolean } {
  let current: unknown = rawData;

  for (const key of keys) {
    if (current == null) return { data: {}, isArray: false };

    if (key === "*") {
      if (Array.isArray(current) && current.length > 0) {
        current = current[0];
      } else if (typeof current === "object" && current !== null) {
        const vals = Object.values(current);
        current = vals.length > 0 ? vals[0] : undefined;
      } else {
        return { data: {}, isArray: false };
      }
    } else {
      const idx = Number(key);
      if (!Number.isNaN(idx) && Array.isArray(current)) {
        current = current[idx];
      } else if (typeof current === "object" && current !== null && key in current) {
        current = (current as Record<string, unknown>)[key];
      } else {
        return { data: {}, isArray: false };
      }
    }
  }

  const isArray = Array.isArray(current);
  return { data: current && typeof current === "object" ? current : {}, isArray };
}

type UseSpanSelectorParams = {
  spans: NestedSpanWithMetricsResponse[];
  path: string;
  name: string;
  onFieldChange: (value: { value: string; name: string; path: string; span_name?: string; attribute_path?: string }) => void;
};

export const useSpanSelector = ({ spans, path, name, onFieldChange }: UseSpanSelectorParams) => {
  // Track if user has manually navigated (overriding path)
  const [manualNavigation, setManualNavigation] = useState<{ spanId: string | null; keys: string[] } | null>(null);

  // Parse path to get initial state
  const pathState = useMemo(() => {
    if (!path) {
      return { spanId: null, keys: [] };
    }

    // Try to match the path against each span's name to find the longest matching span name
    // This handles span names that contain dots or special characters
    let matchedSpan: NestedSpanWithMetricsResponse | undefined;
    let remainingPath = "";

    for (const span of spans) {
      if (span.span_name && path.startsWith(span.span_name + ".")) {
        // Check if this is a longer match than what we have
        if (!matchedSpan || span.span_name.length > matchedSpan.span_name!.length) {
          matchedSpan = span;
          remainingPath = path.slice(span.span_name.length + 1); // +1 for the dot
        }
      }
    }

    if (!matchedSpan) {
      return { spanId: null, keys: [] };
    }

    const attributePath = remainingPath.split(".");
    const navigationKeys = attributePath.slice(0, -1); // Navigate to parent of final attribute

    // Validate that the navigation path exists in the span's data
    if (navigationKeys.length > 0) {
      if (navigationKeys.includes("*")) {
        const { data } = resolveNavigationData(matchedSpan.raw_data, navigationKeys);
        if (!data || typeof data !== "object") {
          return { spanId: null, keys: [] };
        }
        const finalAttribute = attributePath[attributePath.length - 1];
        if (finalAttribute && typeof data === "object" && data !== null && !(finalAttribute in data)) {
          return { spanId: null, keys: [] };
        }
      } else {
        const navPath = navigationKeys.join(".");
        const data = getNestedValue(matchedSpan.raw_data, navPath);

        // If the navigation path doesn't exist or isn't an object, don't use it
        if (!data || typeof data !== "object") {
          return { spanId: null, keys: [] };
        }

        // Also check if the final attribute exists in the data
        const finalAttribute = attributePath[attributePath.length - 1];
        if (finalAttribute && !(finalAttribute in data)) {
          return { spanId: null, keys: [] };
        }
      }
    }

    return {
      spanId: matchedSpan.span_id,
      keys: navigationKeys,
    };
  }, [path, spans]);

  // Use manual navigation if available, otherwise use path-derived state
  const selectedSpanId = manualNavigation !== null ? manualNavigation.spanId : pathState.spanId;
  const selectedKeys = manualNavigation !== null ? manualNavigation.keys : pathState.keys;

  const navigationPath = selectedKeys.join(".");

  const selectedSpan = spans.find((span) => span.span_id === selectedSpanId);

  const { data: currentData, isArray: isCurrentDataArray } = useMemo(() => {
    if (!selectedSpan) return { data: {} as Record<string, unknown>, isArray: false };
    if (selectedKeys.length === 0) return { data: selectedSpan.raw_data as Record<string, unknown>, isArray: false };
    return resolveNavigationData(selectedSpan.raw_data, selectedKeys) as { data: Record<string, unknown>; isArray: boolean };
  }, [selectedSpan, selectedKeys]);

  const availableAttributes = useMemo(() => {
    const keys = Object.keys(currentData);
    return isCurrentDataArray ? ["*", ...keys] : keys;
  }, [currentData, isCurrentDataArray]);

  const getFullPath = (key: string) => (navigationPath ? `${navigationPath}.${key}` : key);

  const getAttributeValue = (key: string) => {
    if (!selectedSpan) return undefined;
    const fullPath = getFullPath(key);
    if (fullPath.includes("*")) {
      // Resolve through wildcards by peeking at first elements for preview
      const { data } = resolveNavigationData(selectedSpan.raw_data, fullPath.split("."));
      return data;
    }
    return getNestedValue(selectedSpan.raw_data, fullPath);
  };

  const selectedAttribute = useMemo(() => {
    if (!path || !selectedSpan) return null;

    const spanNamePrefix = `${selectedSpan.span_name}.`;
    const pathToCheck = path.startsWith(spanNamePrefix) ? path.slice(spanNamePrefix.length) : path;

    return availableAttributes.find((attribute) => (navigationPath ? `${navigationPath}.${attribute}` : attribute) === pathToCheck) ?? null;
  }, [path, selectedSpan, navigationPath, availableAttributes]);

  const handleSelectKey = (key: string) => {
    setManualNavigation({ spanId: selectedSpanId, keys: [...selectedKeys, key] });
  };

  const handleGoBack = () => {
    if (selectedKeys.length === 0) {
      setManualNavigation({ spanId: null, keys: [] });
    } else {
      setManualNavigation({ spanId: selectedSpanId, keys: selectedKeys.slice(0, -1) });
    }
  };

  const handleSelectValue = (key: string) => {
    if (!selectedSpan) return;

    const fullPath = getFullPath(key);

    if (fullPath.includes("*")) {
      const wildcardResults = getNestedValueWildcard(selectedSpan.raw_data, fullPath);
      onFieldChange({
        value: JSON.stringify(wildcardResults ?? []),
        name,
        path: `${selectedSpan.span_name}.${fullPath}`,
        span_name: selectedSpan.span_name || undefined,
        attribute_path: fullPath,
      });
    } else {
      const value = getNestedValue(selectedSpan.raw_data, fullPath);
      onFieldChange({
        value: isPrimitive(value) ? String(value) : JSON.stringify(value),
        name,
        path: `${selectedSpan.span_name}.${fullPath}`,
        span_name: selectedSpan.span_name || undefined,
        attribute_path: fullPath,
      });
    }

    // Clear manual navigation since we've made a selection
    setManualNavigation(null);
  };

  const handleSelectSpan = (spanId: string) => {
    setManualNavigation({ spanId, keys: [] });
  };

  const handleNavigateToAttribute = (e: React.MouseEvent, attribute: string) => {
    e.stopPropagation();
    handleSelectKey(attribute);
  };

  return {
    selectedSpan,
    navigationPath,
    availableAttributes,
    selectedAttribute,
    getAttributeValue,
    handleGoBack,
    handleSelectValue,
    handleSelectSpan,
    handleNavigateToAttribute,
  };
};
