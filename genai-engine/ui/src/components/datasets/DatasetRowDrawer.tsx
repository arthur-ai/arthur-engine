import CloseIcon from "@mui/icons-material/Close";
import { Box, CircularProgress, Drawer, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import React from "react";

import { DatasetRowContent } from "./DatasetRowContent";

import { useApiQuery } from "@/hooks/useApiQuery";

interface DatasetRowDrawerProps {
  open: boolean;
  onClose: () => void;
  datasetId: string;
  versionNumber: number | undefined;
  rowId: string | null;
  taskId?: string;
  onOpenSourceTrace?: (traceId: string) => void;
}

// Read-only row-detail drawer for the dataset viewer. Fetches a single row via the same
// endpoint the experiment "Dataset Row Data" modal uses, driven by the `?row=` URL param.
export const DatasetRowDrawer: React.FC<DatasetRowDrawerProps> = ({ open, onClose, datasetId, versionNumber, rowId, taskId, onOpenSourceTrace }) => {
  const {
    data: rowData,
    isLoading,
    error,
  } = useApiQuery<"getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet">({
    method: "getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet",
    args: [datasetId, versionNumber!, rowId!] as const,
    enabled: open && !!rowId && versionNumber !== undefined,
  });

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
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Tooltip>
        </Stack>

        <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
          {isLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 8 }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 8 }}>
              <Typography color="error">{error.message || "Failed to load dataset row"}</Typography>
            </Box>
          ) : rowData && rowId && versionNumber !== undefined ? (
            <DatasetRowContent
              rowData={rowData}
              datasetId={datasetId}
              versionNumber={versionNumber}
              rowId={rowId}
              taskId={taskId}
              onOpenSourceTrace={onOpenSourceTrace}
            />
          ) : null}
        </Box>
      </Stack>
    </Drawer>
  );
};
