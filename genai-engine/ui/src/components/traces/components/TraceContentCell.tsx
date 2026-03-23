import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { Box, IconButton, Tooltip } from "@mui/material";
import React, { useMemo, useState } from "react";

import { TraceContentModal } from "./TraceContentModal";

import { EVENT_NAMES, track } from "@/services/amplitude";

interface TraceContentCellProps {
  value: unknown;
  title: string;
  traceId?: string | null;
  spanId?: string | null;
  maxLength?: number;
}

const DEFAULT_TRUNCATION_LENGTH = 100;

const getCellValue = (value: unknown) => {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    // JSON.stringify failed (e.g. circular reference). Use a replacer to handle
    // circular refs rather than falling back to .toString() which produces
    // "[object Object],[object Object]" for arrays of objects.
    try {
      const seen = new WeakSet();
      return JSON.stringify(value, (_, v) => {
        if (typeof v === "object" && v !== null) {
          if (seen.has(v)) return "[Circular]";
          seen.add(v);
        }
        return v;
      });
    } catch {
      return String(value);
    }
  }
};

export const TraceContentCell: React.FC<TraceContentCellProps> = ({ value, title, traceId, spanId, maxLength = DEFAULT_TRUNCATION_LENGTH }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const fullValue = useMemo(() => getCellValue(value), [value]);
  const isTruncated = fullValue.length > maxLength;
  const displayValue = isTruncated ? fullValue.slice(0, maxLength) : fullValue;

  const handleOpenModal = (event: React.MouseEvent) => {
    event.stopPropagation();
    if (isTruncated) {
      track(EVENT_NAMES.TRACING_CONTENT_MODAL_OPENED, {
        level: spanId ? "span" : "trace",
        trace_id: traceId,
        span_id: spanId,
        title,
        content_length: fullValue.length,
      });
      setIsModalOpen(true);
    }
  };

  if (!fullValue) return "-";

  return (
    <>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          cursor: isTruncated ? "pointer" : "default",
        }}
        onClick={isTruncated ? handleOpenModal : undefined}
      >
        {isTruncated ? (
          <>
            <Tooltip title={fullValue} arrow placement="top">
              <span className="w-full truncate p-2 bg-gray-100 dark:bg-gray-800 rounded-md">{displayValue}</span>
            </Tooltip>
            <IconButton
              size="small"
              sx={{
                opacity: 0.5,
                "&:hover": { opacity: 1 },
                padding: 0.25,
                flexShrink: 0,
              }}
              onClick={handleOpenModal}
              title="View full content"
            >
              <OpenInFullIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </>
        ) : (
          <span className="w-full p-2">{displayValue}</span>
        )}
      </Box>

      <TraceContentModal open={isModalOpen} onClose={() => setIsModalOpen(false)} title={title} value={fullValue} traceId={traceId} spanId={spanId} />
    </>
  );
};
