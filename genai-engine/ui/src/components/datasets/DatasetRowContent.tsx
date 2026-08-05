import { Box, Link, Typography } from "@mui/material";
import React from "react";
import { Link as RouterLink } from "react-router";

import { CopyableChip } from "@/components/common/CopyableChip";
import { SourceTraceLink } from "@/components/common/SourceTraceLink";
import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

interface DatasetRowContentProps {
  rowData: DatasetVersionRowResponse;
  datasetId: string;
  versionNumber: number;
  rowId: string;
  taskId?: string;
  onOpenSourceTrace?: (traceId: string) => void;
  // When set, the Row ID renders as a router link to the dataset row (e.g. from the experiment modal).
  rowIdHref?: string;
}

// Shared read-only body for a single dataset row — rendered by both the experiment
// "Dataset Row Data" modal and the dataset viewer's row-detail drawer so they stay identical.
export const DatasetRowContent: React.FC<DatasetRowContentProps> = ({
  rowData,
  datasetId,
  versionNumber,
  rowId,
  taskId,
  onOpenSourceTrace,
  rowIdHref,
}) => (
  <Box>
    <Box className="mb-4">
      <Typography variant="body2" className="text-gray-600 dark:text-gray-400 mb-2">
        Dataset: {datasetId} | Version: {versionNumber} | Row ID:{" "}
        {rowIdHref ? (
          <Link component={RouterLink} to={rowIdHref} sx={{ fontFamily: "monospace" }}>
            {rowId}
          </Link>
        ) : (
          rowId
        )}
      </Typography>
      {rowData.trace_id && (
        <Box className="flex items-center gap-1">
          <Typography variant="body2" className="text-gray-600 dark:text-gray-400">
            Source trace:
          </Typography>
          {taskId ? (
            <SourceTraceLink
              variant="field"
              taskId={taskId}
              traceId={rowData.trace_id}
              onOpen={onOpenSourceTrace ? () => onOpenSourceTrace(rowData.trace_id!) : undefined}
            />
          ) : (
            <CopyableChip label={rowData.trace_id} />
          )}
        </Box>
      )}
    </Box>
    <Box className="space-y-3">
      {rowData.data.map((item, index) => (
        <Box key={index} className="p-4 bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
          <Typography variant="subtitle2" className="font-semibold text-gray-700 dark:text-gray-300 mb-1">
            {item.column_name}
          </Typography>
          <Typography variant="body2" className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap wrap-break-word">
            {item.column_value}
          </Typography>
        </Box>
      ))}
    </Box>
  </Box>
);
