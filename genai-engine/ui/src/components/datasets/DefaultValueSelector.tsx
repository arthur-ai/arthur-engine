import {
  Box,
  FormControl,
  MenuItem,
  Select,
  SelectChangeEvent,
  TextField,
  Typography,
} from "@mui/material";
import React, { useState } from "react";

import type { ColumnDefaultConfig, ColumnDefaultType } from "@/types/dataset";

interface DefaultValueSelectorProps {
  value: ColumnDefaultConfig;
  onChange: (config: ColumnDefaultConfig) => void;
  disabled?: boolean;
}

export const DefaultValueSelector: React.FC<DefaultValueSelectorProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  const [showStaticInput, setShowStaticInput] = useState(
    value.type === "static"
  );

  const handleTypeChange = (event: SelectChangeEvent<ColumnDefaultType>) => {
    const newType = event.target.value as ColumnDefaultType;

    if (newType === "static") {
      setShowStaticInput(true);
      onChange({ type: "static", value: value.value ?? "" });
    } else {
      setShowStaticInput(false);
      onChange({ type: newType });
    }
  };

  const handleStaticValueChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    onChange({ type: "static", value: event.target.value });
  };

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
      <FormControl size="small" sx={{ minWidth: 130 }}>
        <Select
          value={value.type}
          onChange={handleTypeChange}
          disabled={disabled}
          size="small"
          sx={{ fontSize: "0.875rem" }}
        >
          <MenuItem value="none">
            <Typography variant="body2">None</Typography>
          </MenuItem>
          <MenuItem value="static">
            <Typography variant="body2">Static value</Typography>
          </MenuItem>
          <MenuItem value="timestamp">
            <Typography variant="body2">Timestamp</Typography>
          </MenuItem>
        </Select>
      </FormControl>

      {showStaticInput && value.type === "static" && (
        <TextField
          size="small"
          placeholder="Default value..."
          value={value.value ?? ""}
          onChange={handleStaticValueChange}
          disabled={disabled}
          sx={{
            minWidth: 120,
            maxWidth: 200,
            "& .MuiInputBase-input": {
              fontSize: "0.875rem",
            },
          }}
        />
      )}
    </Box>
  );
};
