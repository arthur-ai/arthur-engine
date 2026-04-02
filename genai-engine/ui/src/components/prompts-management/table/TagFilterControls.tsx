import ClearIcon from "@mui/icons-material/Clear";
import FilterListIcon from "@mui/icons-material/FilterList";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React from "react";

interface TagFilterControlsProps {
  availableProductionTag: boolean;
  availableCustomTags: string[];
  selectedTags: string[];
  onTagToggle: (tag: string) => void;
  onClearAll: () => void;
}

const PRODUCTION_TAG = "production";

const TagFilterControls: React.FC<TagFilterControlsProps> = ({
  availableProductionTag,
  availableCustomTags,
  selectedTags,
  onTagToggle,
  onClearAll,
}) => {
  const hasAvailableTags = availableProductionTag || availableCustomTags.length > 0;

  if (!hasAvailableTags) return null;

  const hasActiveFilters = selectedTags.length > 0;

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        px: 3,
        py: 1.5,
        flexWrap: "wrap",
        borderBottom: 1,
        borderColor: "divider",
        backgroundColor: "background.paper",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, color: "text.secondary", mr: 0.5 }}>
        <FilterListIcon sx={{ fontSize: 18 }} />
        <Typography variant="caption" sx={{ fontWeight: 600, whiteSpace: "nowrap" }}>
          Filter by tag:
        </Typography>
      </Box>

      {availableProductionTag && (
        <Chip
          label={PRODUCTION_TAG}
          size="small"
          color="success"
          variant={selectedTags.includes(PRODUCTION_TAG) ? "filled" : "outlined"}
          onClick={() => onTagToggle(PRODUCTION_TAG)}
          sx={{ height: 24, fontSize: "0.75rem", cursor: "pointer" }}
        />
      )}

      {availableCustomTags.map((tag) => (
        <Chip
          key={tag}
          label={tag}
          size="small"
          color="primary"
          variant={selectedTags.includes(tag) ? "filled" : "outlined"}
          onClick={() => onTagToggle(tag)}
          sx={{ height: 24, fontSize: "0.75rem", cursor: "pointer" }}
        />
      ))}

      {hasActiveFilters && (
        <Tooltip title="Clear all tag filters">
          <IconButton size="small" onClick={onClearAll} sx={{ ml: 0.5, color: "text.secondary" }} aria-label="Clear tag filters">
            <ClearIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Tooltip>
      )}
    </Box>
  );
};

export default TagFilterControls;
