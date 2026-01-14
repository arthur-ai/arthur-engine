import type { SxProps, Theme } from "@mui/material/styles";

import type { ExperimentStatus } from "@/lib/api-client/api-client";

interface StatusColors {
  color: string;
  borderColor: string;
  bgColor?: string;
}

const STATUS_COLOR_MAP: Record<string, StatusColors> = {
  queued: { color: "text.secondary", borderColor: "text.secondary" },
  running: { color: "primary.main", borderColor: "primary.main", bgColor: "primary.50" },
  evaluating: { color: "info.main", borderColor: "info.main", bgColor: "info.50" },
  completed: { color: "success.main", borderColor: "success.main" },
  failed: { color: "error.main", borderColor: "error.main" },
};

/**
 * Get MUI sx props for status chip styling based on experiment status
 * Used across RAG notebooks, experiment history, and experiment details
 */
export function getStatusChipSx(status: ExperimentStatus | string | undefined): SxProps<Theme> {
  if (!status) return {};

  const colors = STATUS_COLOR_MAP[status] || STATUS_COLOR_MAP.queued;
  return {
    backgroundColor: colors.bgColor || "transparent",
    color: colors.color,
    borderColor: colors.borderColor,
    borderWidth: 1,
    borderStyle: "solid",
    textTransform: "capitalize",
    fontWeight: 500,
  };
}
