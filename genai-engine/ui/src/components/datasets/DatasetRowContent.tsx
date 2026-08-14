import { Box, Link, Stack, Typography } from "@mui/material";
import React from "react";
import { Link as RouterLink } from "react-router";

import { CopyableChip } from "@/components/common/CopyableChip";
import { SourceTraceLink } from "@/components/common/SourceTraceLink";
import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { track } from "@/services/analytics";

interface DatasetRowContentProps {
  rowData: DatasetVersionRowResponse;
  datasetId: string;
  versionNumber: number;
  rowId: string;
  taskId?: string;
  onOpenSourceTrace?: (traceId: string) => void;
  // Experiment context only: renders an explicit link to this row in the dataset viewer.
  openInDatasetHref?: string;
}

// Shared read-only body for a single dataset row — rendered by the row drawer on both
// the experiment results page and the dataset viewer so they stay identical.
export const DatasetRowContent: React.FC<DatasetRowContentProps> = ({
  rowData,
  datasetId,
  versionNumber,
  rowId,
  taskId,
  onOpenSourceTrace,
  openInDatasetHref,
}) => (
  <Stack spacing={3}>
    <Stack spacing={1}>
      <Stack direction="row" alignItems="center" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
        <Typography variant="body2" color="text.secondary">
          Dataset: {datasetId} | Version: {versionNumber} | Row ID:
        </Typography>
        <CopyableChip label={rowId} size="small" />
        {openInDatasetHref && (
          <Link
            component={RouterLink}
            to={openInDatasetHref}
            variant="body2"
            onClick={() => {
              if (taskId) {
                track("dataset/open_row_from_experiment", { task_id: taskId, dataset_id: datasetId, source: "experiment_drawer" });
              }
            }}
          >
            Open in dataset
          </Link>
        )}
      </Stack>
      {rowData.trace_id && (
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography variant="body2" color="text.secondary">
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
        </Stack>
      )}
    </Stack>
    <Stack spacing={1.5}>
      {rowData.data.map((item) => (
        <Box key={item.column_name} sx={{ p: 2, backgroundColor: "action.hover", borderRadius: 1, border: "1px solid", borderColor: "divider" }}>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            {item.column_name}
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {item.column_value}
          </Typography>
        </Box>
      ))}
    </Stack>
  </Stack>
);
