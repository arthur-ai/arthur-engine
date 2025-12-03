import { useMemo, useState } from "react";

import { getNestedValue } from "../../../utils/spans";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

const isPrimitive = (value: unknown): value is string | number | boolean | null | undefined => {
  return typeof value !== "object" || value === null;
};

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
    let remainingPath = '';

    for (const span of spans) {
      if (span.span_name && path.startsWith(span.span_name + '.')) {
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

    const attributePath = remainingPath.split('.');
    const navigationKeys = attributePath.slice(0, -1); // Navigate to parent of final attribute

    // Validate that the navigation path exists in the span's data
    if (navigationKeys.length > 0) {
      const navPath = navigationKeys.join('.');
      const data = getNestedValue(matchedSpan.raw_data, navPath);

      // If the navigation path doesn't exist or isn't an object, don't use it
      if (!data || typeof data !== 'object') {
        return { spanId: null, keys: [] };
      }

      // Also check if the final attribute exists in the data
      const finalAttribute = attributePath[attributePath.length - 1];
      if (finalAttribute && !(finalAttribute in data)) {
        return { spanId: null, keys: [] };
      }
    }

    return {
      spanId: matchedSpan.span_id,
      keys: navigationKeys,
    };
  }, [path, spans]);

  // Use manual navigation if available, otherwise use path-derived state
  const selectedSpanId = manualNavigation?.spanId ?? pathState.spanId;
  const selectedKeys = manualNavigation?.keys ?? pathState.keys;

  const navigationPath = selectedKeys.join(".");

  const selectedSpan = spans.find((span) => span.span_id === selectedSpanId);

  const currentData = useMemo(() => {
    if (!selectedSpan) return {};
    const data = navigationPath ? getNestedValue(selectedSpan.raw_data, navigationPath) : selectedSpan.raw_data;
    return data && typeof data === "object" ? data : {};
  }, [selectedSpan, navigationPath]);

  const availableAttributes = Object.keys(currentData);

  const getFullPath = (key: string) => (navigationPath ? `${navigationPath}.${key}` : key);
  const getAttributeValue = (key: string) => getNestedValue(selectedSpan?.raw_data, getFullPath(key));

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
    const value = getNestedValue(selectedSpan?.raw_data, fullPath);

    onFieldChange({
      value: isPrimitive(value) ? String(value) : JSON.stringify(value),
      name,
      path: `${selectedSpan.span_name}.${fullPath}`,
      span_name: selectedSpan.span_name || undefined,
      attribute_path: fullPath,
    });

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
