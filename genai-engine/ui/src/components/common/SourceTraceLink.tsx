import ArrowOutwardIcon from "@mui/icons-material/ArrowOutward";
import { Button, Link as MuiLink, Typography } from "@mui/material";
import React from "react";
import { Link as RouterLink } from "react-router";

import { serializeDrawerTarget } from "@/components/traces/hooks/useDrawerTarget";

export function traceDeepLinkPath(taskId: string, traceId: string): string {
  return `/tasks/${taskId}/traces${serializeDrawerTarget({ target: "trace", id: traceId })}`;
}

export function truncateTraceId(traceId: string): string {
  return traceId.length > 14 ? `${traceId.slice(0, 8)}…${traceId.slice(-4)}` : traceId;
}

interface SourceTraceLinkProps {
  taskId: string;
  traceId: string;
  /**
   * subtle — small secondary-text "Source trace" label, no id (dataset table rows)
   * field — monospace trace id, sits next to a metadata label (row modals)
   * pill — outlined "View originating trace · <truncated id>" button (test-case header)
   */
  variant: "subtle" | "field" | "pill";
}

export const SourceTraceLink: React.FC<SourceTraceLinkProps> = ({ taskId, traceId, variant }) => {
  const to = traceDeepLinkPath(taskId, traceId);
  const newTabProps = { target: "_blank", rel: "noopener noreferrer" } as const;

  if (variant === "pill") {
    return (
      <Button
        component={RouterLink}
        to={to}
        {...newTabProps}
        variant="outlined"
        size="small"
        startIcon={<ArrowOutwardIcon sx={{ fontSize: 14 }} />}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
        sx={{ borderRadius: 999, textTransform: "none", whiteSpace: "nowrap" }}
      >
        View originating trace ·&nbsp;
        <Typography component="span" variant="body2" sx={{ fontFamily: "monospace" }}>
          {truncateTraceId(traceId)}
        </Typography>
      </Button>
    );
  }

  if (variant === "field") {
    return (
      <MuiLink
        component={RouterLink}
        to={to}
        {...newTabProps}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
        sx={{ display: "inline-flex", alignItems: "center", gap: 0.5, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
      >
        <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
          {traceId}
        </Typography>
        <ArrowOutwardIcon sx={{ fontSize: 14 }} />
      </MuiLink>
    );
  }

  return (
    <MuiLink
      component={RouterLink}
      to={to}
      {...newTabProps}
      onClick={(e: React.MouseEvent) => e.stopPropagation()}
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.25,
        color: "text.secondary",
        textDecoration: "none",
        "&:hover": { color: "primary.main", textDecoration: "underline" },
      }}
    >
      <ArrowOutwardIcon sx={{ fontSize: 12 }} />
      <Typography variant="caption">Source trace</Typography>
    </MuiLink>
  );
};
