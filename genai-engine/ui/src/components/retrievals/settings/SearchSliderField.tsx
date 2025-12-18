import { Slider, Stack, Typography } from "@mui/material";
import React from "react";

interface SearchSliderFieldProps {
  label: string;
  helperText?: string;
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  min?: number;
  max?: number;
  step?: number;
  formatValue?: (value: number) => string;
}

const clampValue = (value: number, min: number, max: number): number => {
  if (Number.isNaN(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
};

export const SearchSliderField: React.FC<SearchSliderFieldProps> = React.memo(
  ({ label, helperText, value, onChange, disabled = false, min = 0, max = 1, step = 0.01, formatValue }) => {
    const displayValue = formatValue ? formatValue(value) : value.toString();

    const handleSliderChange = (_event: Event, newValue: number | number[]) => {
      if (typeof newValue === "number") {
        const normalized = clampValue(newValue, min, max);
        onChange(normalized);
      }
    };

    return (
      <Stack spacing={1}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Stack spacing={0.5} flexGrow={1}>
            <Typography variant="subtitle2" color="text.primary">
              {label}
            </Typography>
            {helperText ? (
              <Typography variant="caption" color="text.secondary">
                {helperText}
              </Typography>
            ) : null}
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ minWidth: 48, textAlign: "right" }}>
            {displayValue}
          </Typography>
        </Stack>
        <Slider value={value} onChange={handleSliderChange} min={min} max={max} step={step} disabled={disabled} aria-label={label} />
      </Stack>
    );
  }
);
