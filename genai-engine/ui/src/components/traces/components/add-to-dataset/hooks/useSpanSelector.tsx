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
  onFieldChange: (value: { value: string; name: string; path: string }) => void;
};

export const useSpanSelector = ({ spans, path, name, onFieldChange }: UseSpanSelectorParams) => {
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);

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
    setSelectedKeys((prev) => [...prev, key]);
  };

  const handleGoBack = () => {
    if (selectedKeys.length === 0) {
      setSelectedSpanId(null);
    } else {
      setSelectedKeys((prev) => prev.slice(0, -1));
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
    });
  };

  const handleSelectSpan = (spanId: string) => {
    setSelectedSpanId(spanId);
    setSelectedKeys([]);
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
