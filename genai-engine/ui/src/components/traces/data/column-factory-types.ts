import type { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import type { SxProps, Theme } from "@mui/material/styles";
import type React from "react";

import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";

export type ColumnDependencies = {
  formatDate: (date: string | null | undefined) => string;
  formatCurrency: (amount: number) => string;
  onTrack: (event: string, properties?: Record<string, unknown>) => void;
  Chip: React.ComponentType<{
    label: string;
    onCopy?: (value: string) => void;
    sx?: SxProps<Theme>;
  }>;
  DurationCell: React.ComponentType<{ duration: number }>;
  TraceContentCell: React.ComponentType<{
    value: unknown;
    title: string;
    traceId?: string | null;
    spanId?: string | null;
  }>;
  AnnotationCell: React.ComponentType<{
    annotations: AgenticAnnotationResponse[];
    traceId: string;
  }>;
  SpanStatusBadge: React.ComponentType<{
    status: string;
    disableLabel?: boolean;
    className?: string;
  }>;
  TypeChip: React.ComponentType<{ type: OpenInferenceSpanKind; active?: boolean }>;
  TokenCountTooltip: React.ComponentType<{
    prompt?: number;
    completion?: number;
    total: number;
  }>;
  TokenCostTooltip: React.ComponentType<{
    prompt?: number;
    completion?: number;
    total: number;
  }>;
  isValidStatusCode?: (statusCode: string) => boolean;
};
