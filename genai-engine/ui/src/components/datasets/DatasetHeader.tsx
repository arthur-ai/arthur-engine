import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import HistoryIcon from "@mui/icons-material/History";
import SaveIcon from "@mui/icons-material/Save";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import { Box, Button, IconButton, Typography } from "@mui/material";
import React from "react";

import { DatasetSearchBar } from "./DatasetSearchBar";

interface DatasetHeaderProps {
  datasetName: string;
  description?: string | null;
  hasUnsavedChanges: boolean;
  isSaving: boolean;
  canSave: boolean;
  canAddRow: boolean;
  onBack: () => void;
  onSave: () => void;
  onConfigureColumns: () => void;
  onAddRow: () => void;
  onOpenVersions: () => void;
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
  onBack,
  onSave,
  onConfigureColumns,
  onAddRow,
  onOpenVersions,
  searchValue,
  onSearchChange,
  onSearchClear,
}) => {
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
          {hasUnsavedChanges && (
            <Typography
              variant="caption"
              sx={{ color: "warning.main", fontWeight: 500 }}
            >
              • Unsaved changes
            </Typography>
          )}
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
          startIcon={<HistoryIcon />}
          onClick={onOpenVersions}
        >
          Versions
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
          variant="contained"
          size="small"
          startIcon={<AddIcon />}
          onClick={onAddRow}
          disabled={!canAddRow}
          title={!canAddRow ? "Add at least one column first" : "Add a new row"}
        >
          Add Row
        </Button>
      </Box>
    </Box>
  );
};
