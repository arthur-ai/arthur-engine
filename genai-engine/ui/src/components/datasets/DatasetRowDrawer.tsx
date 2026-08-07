import CloseIcon from "@mui/icons-material/Close";
import { Alert, Box, CircularProgress, Drawer, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import { isAxiosError } from "axios";
import React, { useState } from "react";

import { DatasetRowContent } from "./DatasetRowContent";

import { useDatasetRow } from "@/hooks/useDatasetRow";
import { getApiErrorMessage } from "@/utils/errorUtils";

interface DatasetRowDrawerProps {
  open: boolean;
  onClose: () => void;
  datasetId: string;
  versionNumber: number | undefined;
  rowId: string | null;
  taskId?: string;
  onOpenSourceTrace?: (traceId: string) => void;
  openInDatasetHref?: string;
}

// Read-only row-detail drawer, shared by the dataset viewer (driven by the `?row=` URL
// param) and the experiment results page (driven by local state).
export const DatasetRowDrawer: React.FC<DatasetRowDrawerProps> = ({
  open,
  onClose,
  datasetId,
  versionNumber,
  rowId,
  taskId,
  onOpenSourceTrace,
  openInDatasetHref,
}) => {
  // rowId is retained on close so the drawer's exit animation doesn't unmount its content mid-slide
  const [retainedRowId, setRetainedRowId] = useState(rowId);
  if (rowId && rowId !== retainedRowId) {
    setRetainedRowId(rowId);
  }
  const effectiveRowId = rowId ?? retainedRowId;

  const { data: rowData, isLoading, error } = useDatasetRow(datasetId, versionNumber, effectiveRowId, open);

  // The row query is disabled until the version resolves, and react-query reports
  // isLoading=false while disabled — treat that window as loading, not empty.
  const pendingVersion = open && !!effectiveRowId && versionNumber === undefined;

  return (
    <Drawer open={open} onClose={onClose} anchor="right" slotProps={{ paper: { sx: { width: { xs: "100%", sm: 520 } } } }}>
      <Stack direction="column" sx={{ height: "100%" }}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: "divider", backgroundColor: "background.paper" }}
        >
          <Typography variant="subtitle1" fontWeight={600} color="text.primary">
            Dataset Row Data
          </Typography>
          <Tooltip title="Close">
            <IconButton onClick={onClose} size="small" aria-label="Close">
              <CloseIcon />
            </IconButton>
          </Tooltip>
        </Stack>

        <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
          {isLoading || pendingVersion ? (
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 8 }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            isAxiosError(error) && error.response?.status === 404 ? (
              <Alert severity="warning">Row not found in this dataset version</Alert>
            ) : (
              <Alert severity="error">{getApiErrorMessage(error, "Failed to load dataset row")}</Alert>
            )
          ) : rowData && effectiveRowId && versionNumber !== undefined ? (
            <DatasetRowContent
              rowData={rowData}
              datasetId={datasetId}
              versionNumber={versionNumber}
              rowId={effectiveRowId}
              taskId={taskId}
              onOpenSourceTrace={onOpenSourceTrace}
              openInDatasetHref={openInDatasetHref}
            />
          ) : null}
        </Box>
      </Stack>
    </Drawer>
  );
};
