import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import { IconButton, TextField } from "@mui/material";
import React from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
  placeholder?: string;
  fullWidth?: boolean;
  size?: "small" | "medium";
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  onClear,
  placeholder = "Search...",
  fullWidth = true,
  size = "small",
}) => {
  return (
    <TextField
      fullWidth={fullWidth}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      variant="outlined"
      size={size}
      slotProps={{
        input: {
          startAdornment: (
            <SearchIcon
              fontSize="small"
              sx={{ mr: 1, color: "action.active" }}
            />
          ),
          endAdornment: value && onClear && (
            <IconButton size="small" onClick={onClear} edge="end">
              <ClearIcon fontSize="small" />
            </IconButton>
          ),
        },
      }}
    />
  );
};
