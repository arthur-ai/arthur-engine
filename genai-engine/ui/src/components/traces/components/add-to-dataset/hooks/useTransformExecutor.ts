import { useMemo } from "react";

import { TransformDefinition, Column } from "../form/shared";
import { executeTransform } from "../utils/transformExecutor";

import { NestedSpanWithMetricsResponse } from "@/lib/api-client/api-client";

// Executes transform on spans with memoization
export function useTransformExecutor(spans: NestedSpanWithMetricsResponse[], transform: TransformDefinition | undefined): Column[] | null {
  return useMemo(() => {
    if (!transform) return null;
    return executeTransform(spans, transform);
  }, [spans, transform]);
}
