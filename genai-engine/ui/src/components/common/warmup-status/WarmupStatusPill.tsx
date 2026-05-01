import WarningAmberOutlined from "@mui/icons-material/WarningAmberOutlined";
import { Box, Chip, CircularProgress, Stack, Tooltip, Typography } from "@mui/material";

import type { ModelLoadStatus, ModelStatusEntry, ModelStatusResponse } from "@/lib/api-client/api-client";

export interface WarmupStatusPillCopy {
  /** Label rendered while the engine is still loading models. */
  warming: (ready: number, total: number) => string;
  /** Label rendered when at least one model failed or was skipped. */
  degraded: (unavailable: number) => string;
  /** Reassurance string shown at the top of the tooltip. */
  tooltipReassurance: string;
  /** Section heading shown above the per-model breakdown in the tooltip. */
  tooltipHeading: string;
}

const DEFAULT_COPY: WarmupStatusPillCopy = {
  warming: (ready, total) => `Models warming up (${ready}/${total})`,
  degraded: (unavailable) => `${unavailable} model${unavailable === 1 ? "" : "s"} unavailable`,
  tooltipReassurance:
    "This is not a failure — the engine is still loading models. Some checks may be temporarily unavailable; they'll start running automatically once ready.",
  tooltipHeading: "Per-model status",
};

const WARMING_STATES = new Set<ModelLoadStatus>(["pending", "downloading", "loading"]);
const UNAVAILABLE_STATES = new Set<ModelLoadStatus>(["failed", "skipped"]);

export interface WarmupStatusPillViewProps {
  /** Pre-fetched payload. When `undefined` the component renders nothing. */
  data: ModelStatusResponse | undefined;
  size?: "small" | "medium";
  copy?: Partial<WarmupStatusPillCopy>;
}

/**
 * Presentational pill — takes a fully-resolved `ModelStatusResponse`.
 * Renders nothing when data is missing or when the engine reports `"ready"`.
 */
export function WarmupStatusPillView({ data, size = "small", copy }: WarmupStatusPillViewProps) {
  if (!data) return null;
  if (data.overall_status === "ready") return null;
  if (!data.models || data.models.length === 0) return null;

  const merged: WarmupStatusPillCopy = { ...DEFAULT_COPY, ...copy };
  const models = data.models ?? [];
  const total = models.length;

  const counts = models.reduce(
    (acc, m) => {
      if (m.status === "ready") acc.ready += 1;
      else if (UNAVAILABLE_STATES.has(m.status)) acc.unavailable += 1;
      else if (WARMING_STATES.has(m.status)) acc.warming += 1;
      return acc;
    },
    { ready: 0, unavailable: 0, warming: 0 }
  );

  const isDegraded =
    data.overall_status === "partial" || data.overall_status === "failed" || data.overall_status === "skipped" || counts.unavailable > 0;

  const label = isDegraded ? merged.degraded(counts.unavailable) : merged.warming(counts.ready, total);

  const icon = isDegraded ? (
    <WarningAmberOutlined sx={{ fontSize: 14 }} />
  ) : (
    <CircularProgress size={12} thickness={5} sx={{ color: "info.main" }} aria-label="warming up" />
  );

  return (
    <Tooltip
      arrow
      placement="bottom-end"
      title={
        <TooltipBody
          reassurance={merged.tooltipReassurance}
          heading={merged.tooltipHeading}
          models={models}
          warmingCount={counts.warming}
          readyCount={counts.ready}
          unavailableCount={counts.unavailable}
        />
      }
    >
      <Chip
        size={size}
        variant="outlined"
        color={isDegraded ? "warning" : "info"}
        icon={icon}
        label={label}
        sx={{
          cursor: "default",
          fontWeight: 500,
          "& .MuiChip-icon": { ml: 0.75, mr: -0.25 },
        }}
      />
    </Tooltip>
  );
}

interface TooltipBodyProps {
  reassurance: string;
  heading: string;
  models: ModelStatusEntry[];
  warmingCount: number;
  readyCount: number;
  unavailableCount: number;
}

function TooltipBody({ reassurance, heading, models, warmingCount, readyCount, unavailableCount }: TooltipBodyProps) {
  return (
    <Box sx={{ maxWidth: 320, py: 0.5 }}>
      <Typography variant="caption" sx={{ display: "block", mb: 1 }}>
        {reassurance}
      </Typography>
      <Stack direction="row" spacing={1.5} sx={{ mb: 1 }}>
        <SummaryToken label="ready" count={readyCount} />
        <SummaryToken label="warming" count={warmingCount} />
        <SummaryToken label="unavailable" count={unavailableCount} />
      </Stack>
      <Typography
        variant="caption"
        sx={{
          display: "block",
          textTransform: "uppercase",
          letterSpacing: 0.5,
          color: "text.secondary",
          mb: 0.5,
        }}
      >
        {heading}
      </Typography>
      <Stack spacing={0.25}>
        {models.map((model) => (
          <ModelRow key={model.key} model={model} />
        ))}
      </Stack>
    </Box>
  );
}

function SummaryToken({ label, count }: { label: string; count: number }) {
  return (
    <Typography variant="caption" sx={{ color: "text.secondary" }}>
      <Typography component="span" variant="caption" sx={{ fontWeight: 600, color: "text.primary", mr: 0.5 }}>
        {count}
      </Typography>
      {label}
    </Typography>
  );
}

function ModelRow({ model }: { model: ModelStatusEntry }) {
  const retryCount = model.retry_count ?? 0;
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="baseline" spacing={1}>
      <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
        {model.key}
      </Typography>
      <Typography
        variant="caption"
        sx={{
          color: statusColor(model.status),
          fontWeight: 500,
        }}
      >
        {model.status}
        {retryCount > 0 ? ` (retry ${retryCount})` : ""}
      </Typography>
    </Stack>
  );
}

function statusColor(status: ModelLoadStatus): string {
  switch (status) {
    case "ready":
      return "success.main";
    case "failed":
      return "error.main";
    case "skipped":
      return "warning.main";
    case "pending":
    case "downloading":
    case "loading":
      return "info.main";
    default: {
      const _exhaustive: never = status;
      throw new Error(`Unhandled model status: ${_exhaustive as string}`);
    }
  }
}
