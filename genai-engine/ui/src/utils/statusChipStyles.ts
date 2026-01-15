import type { SxProps, Theme } from "@mui/material/styles";

interface StatusColors {
  color: string;
  borderColor: string;
  bgColor?: string;
}

/**
 * Comprehensive color map for all status types used across the application
 */
const STATUS_COLOR_MAP: Record<string, StatusColors> = {
  // Experiment statuses
  queued: { color: "text.secondary", borderColor: "text.secondary" },
  running: { color: "primary.main", borderColor: "primary.main", bgColor: "primary.50" },
  evaluating: { color: "info.main", borderColor: "info.main", bgColor: "info.50" },
  completed: { color: "success.main", borderColor: "success.main" },
  failed: { color: "error.main", borderColor: "error.main" },

  // Eval/Annotation statuses
  pending: { color: "text.secondary", borderColor: "text.secondary" },
  passed: { color: "success.main", borderColor: "success.main" },
  error: { color: "error.main", borderColor: "error.main" },
  skipped: { color: "var(--color-neutral-500)", borderColor: "var(--color-neutral-500)" },

  // Generic statuses
  default: { color: "text.secondary", borderColor: "text.secondary" },
  primary: { color: "primary.main", borderColor: "primary.main" },
  info: { color: "info.main", borderColor: "info.main" },
  success: { color: "success.main", borderColor: "success.main" },
};

/**
 * Get MUI sx props for status chip styling based on status string
 */
export function getStatusChipSx(status: string | undefined | null): SxProps<Theme> {
  if (!status) return {};

  const normalizedStatus = status.toLowerCase();
  const colors = STATUS_COLOR_MAP[normalizedStatus] || STATUS_COLOR_MAP.default;

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

/**
 * Get MUI color prop value for status
 */
export function getStatusColor(status: string | undefined | null): "default" | "primary" | "info" | "success" | "error" {
  if (!status) return "default";

  const normalizedStatus = status.toLowerCase();

  switch (normalizedStatus) {
    case "queued":
    case "pending":
      return "default";
    case "running":
      return "primary";
    case "evaluating":
      return "info";
    case "completed":
    case "passed":
    case "success":
      return "success";
    case "failed":
    case "error":
      return "error";
    default:
      return "default";
  }
}
