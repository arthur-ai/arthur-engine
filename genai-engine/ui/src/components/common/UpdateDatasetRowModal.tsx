import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";

import { useApiQuery } from "@/hooks/useApiQuery";
import { useUpdateDatasetRowFromExperiment } from "@/hooks/useUpdateDatasetRowFromExperiment";

interface UpdateDatasetRowModalProps {
  open: boolean;
  onClose: () => void;
  datasetId: string;
  datasetVersion: number;
  rowId: string;
  outputValue: string;
  onSuccess?: () => void;
}

export const UpdateDatasetRowModal: React.FC<UpdateDatasetRowModalProps> = ({
  open,
  onClose,
  datasetId,
  datasetVersion,
  rowId,
  outputValue,
  onSuccess,
}) => {
  const [selectedColumn, setSelectedColumn] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const {
    data: rowData,
    isLoading: isLoadingColumns,
    error: columnsError,
  } = useApiQuery<"getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet">({
    method: "getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet",
    args: [datasetId, datasetVersion, rowId],
    enabled: open && !!datasetId && !!rowId,
  });

  const columns = rowData?.data.map((col) => col.column_name) ?? [];

  const updateMutation = useUpdateDatasetRowFromExperiment(datasetId);

  useEffect(() => {
    if (open) {
      setSelectedColumn("");
      setError(null);
    }
  }, [open]);

  const handleConfirm = async () => {
    if (!selectedColumn) return;

    setError(null);

    try {
      await updateMutation.mutateAsync({
        datasetId,
        datasetVersion,
        rowId,
        columnName: selectedColumn,
        newValue: outputValue,
      });

      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update dataset");
    }
  };

  const handleClose = () => {
    if (!updateMutation.isPending) {
      onClose();
    }
  };

  const isConfirmDisabled = !selectedColumn || updateMutation.isPending || isLoadingColumns;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth aria-labelledby="update-dataset-row-dialog-title">
      <DialogTitle id="update-dataset-row-dialog-title">Update Dataset Row</DialogTitle>
      <DialogContent dividers>
        <Box className="space-y-4">
          <Alert severity="info" sx={{ mb: 2 }}>
            This will create a new dataset version with the updated value in the selected column.
          </Alert>

          {(error || columnsError) && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error || columnsError?.message || "An error occurred"}
            </Alert>
          )}

          <Box>
            <Typography variant="subtitle2" className="font-medium text-gray-700 mb-1">
              Value to insert:
            </Typography>
            <Box
              sx={{
                p: 2,
                backgroundColor: "action.hover",
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
                maxHeight: 200,
                overflow: "auto",
              }}
            >
              <Typography
                variant="body2"
                component="pre"
                sx={{
                  fontFamily: "monospace",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  m: 0,
                }}
              >
                {outputValue}
              </Typography>
            </Box>
          </Box>

          <FormControl fullWidth disabled={updateMutation.isPending}>
            <InputLabel id="column-select-label">Target Column</InputLabel>
            <Select
              labelId="column-select-label"
              id="column-select"
              value={selectedColumn}
              label="Target Column"
              onChange={(e) => setSelectedColumn(e.target.value)}
              disabled={isLoadingColumns || updateMutation.isPending}
            >
              {isLoadingColumns ? (
                <MenuItem disabled value="">
                  <Box className="flex items-center gap-2">
                    <CircularProgress size={16} />
                    <span>Loading columns...</span>
                  </Box>
                </MenuItem>
              ) : columns.length === 0 ? (
                <MenuItem disabled value="">
                  No columns available
                </MenuItem>
              ) : (
                columns.map((column) => (
                  <MenuItem key={column} value={column}>
                    {column}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={updateMutation.isPending} color="inherit">
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          disabled={isConfirmDisabled}
          variant="contained"
          color="primary"
          startIcon={updateMutation.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {updateMutation.isPending ? "Updating..." : "Update Dataset"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
