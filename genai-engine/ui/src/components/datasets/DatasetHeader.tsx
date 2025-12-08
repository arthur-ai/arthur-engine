import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DownloadIcon from "@mui/icons-material/Download";
import HistoryIcon from "@mui/icons-material/History";
import SaveIcon from "@mui/icons-material/Save";
import ScienceIcon from "@mui/icons-material/Science";
import UploadIcon from "@mui/icons-material/Upload";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import { Box, Button, IconButton, Typography } from "@mui/material";
import React from "react";

import { DatasetSearchBar } from "./DatasetSearchBar";

import { MAX_DATASET_ROWS } from "@/constants/datasetConstants";

interface DatasetHeaderProps {
  datasetName: string;
  description?: string | null;
  hasUnsavedChanges: boolean;
  isSaving: boolean;
  canSave: boolean;
  canAddRow: boolean;
  columnCount: number;
  rowCount: number;
  onBack: () => void;
  onSave: () => void;
  onConfigureColumns: () => void;
  onAddRow: () => void;
  onOpenVersions: () => void;
  onExport: () => void;
  onImport: () => void;
  onViewExperiments: () => void;
  searchValue: string;
  onSearchChange: (value: string) => void;
  onSearchClear: () => void;
}

export const DatasetHeader: React.FC<DatasetHeaderProps> = ({
  datasetName,
  description,
  hasUnsavedChanges,
  isSaving,
  canSave,
  canAddRow,
  columnCount,
  rowCount,
  onBack,
  onSave,
  onConfigureColumns,
  onAddRow,
  onOpenVersions,
  onExport,
  onImport,
  onViewExperiments,
  searchValue,
  onSearchChange,
  onSearchClear,
}) => {
  const isAtRowLimit = rowCount >= MAX_DATASET_ROWS;

  const getAddRowTooltip = () => {
    if (!canAddRow) return "Add at least one column first";
    if (isAtRowLimit) return `Maximum row limit (${MAX_DATASET_ROWS}) reached`;
    return "Add a new row";
  };
  return (
    <Box
      sx={{
        px: 3,
        py: 2,
        borderBottom: 1,
        borderColor: "divider",
        backgroundColor: "background.paper",
      }}
    >
      {/* Row 1: Navigation, Title, Stats, Primary Actions */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <IconButton size="small" onClick={onBack}>
          <ArrowBackIcon />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography
            variant="h6"
            sx={{ fontWeight: 600, color: "text.primary" }}
          >
            {datasetName}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {hasUnsavedChanges && (
              <Typography
                variant="caption"
                sx={{ color: "warning.main", fontWeight: 500 }}
              >
                • Unsaved changes
              </Typography>
            )}
            <Typography variant="body2" color="text.secondary">
              {columnCount} column{columnCount !== 1 ? "s" : ""} •{" "}
              {rowCount.toLocaleString()} / {MAX_DATASET_ROWS} rows
            </Typography>
          </Box>
        </Box>
        <Button
          variant="contained"
          color="success"
          size="small"
          startIcon={<SaveIcon />}
          onClick={onSave}
          disabled={!canSave}
        >
          {isSaving ? "Saving..." : "Save"}
        </Button>
        <Button
          variant="outlined"
          size="small"
          startIcon={<DownloadIcon />}
          onClick={onExport}
          disabled={rowCount === 0}
          title={rowCount === 0 ? "No data to export" : "Export to CSV"}
        >
          Export
        </Button>
        <Button
          variant="outlined"
          size="small"
          startIcon={<HistoryIcon />}
          onClick={onOpenVersions}
        >
          Versions
        </Button>
        <Button
          variant="outlined"
          size="small"
          startIcon={<ScienceIcon />}
          onClick={onViewExperiments}
          title="View experiments using this dataset"
        >
          Experiments
        </Button>
      </Box>

      {/* Description */}
      {description && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: 2, ml: 6 }}
        >
          {description}
        </Typography>
      )}

      {/* Row 2: Search Bar and Data Manipulation Actions */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <Box sx={{ flexGrow: 1 }}>
          <DatasetSearchBar
            value={searchValue}
            onChange={onSearchChange}
            onClear={onSearchClear}
          />
        </Box>
        <Button
          variant="outlined"
          size="small"
          startIcon={<ViewColumnIcon />}
          onClick={onConfigureColumns}
        >
          Configure Columns
        </Button>
        <Button
          variant="outlined"
          size="small"
          startIcon={<UploadIcon />}
          onClick={onImport}
          title="Import data from CSV"
        >
          Import
        </Button>
        <Button
          variant="contained"
          size="small"
          startIcon={<AddIcon />}
          onClick={onAddRow}
          disabled={!canAddRow || isAtRowLimit}
          title={getAddRowTooltip()}
        >
          Add Row
        </Button>
      </Box>
    </Box>
  );
};
