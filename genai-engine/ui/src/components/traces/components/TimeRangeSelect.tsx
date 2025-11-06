import { FormControl, InputLabel, MenuItem, Select } from "@mui/material";

import { TIME_RANGES, type TimeRange } from "../constants";

type Props = {
  value: TimeRange;
  onValueChange: (value: TimeRange) => void;
};

export const TimeRangeSelect = ({ value, onValueChange }: Props) => {
  return (
    <FormControl size="small" sx={{ ml: "auto" }}>
      <InputLabel id="time-range-label">Time range</InputLabel>
      <Select
        labelId="time-range-label"
        label="Time range"
        size="small"
        value={value}
        onChange={(event) => onValueChange(event.target.value as TimeRange)}
      >
        {Object.entries(TIME_RANGES).map(([key, value]) => (
          <MenuItem key={key} value={value}>
            {TIME_RANGE_TO_LABEL[key as keyof typeof TIME_RANGE_TO_LABEL]}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

const TIME_RANGE_TO_LABEL = {
  "5 minutes": "Past 5 minutes",
  "30 minutes": "Past 30 minutes",
  "1 day": "Past 1 day",
  "1 week": "Past 1 week",
  "1 month": "Past 1 month",
  "3 months": "Past 3 months",
  "1 year": "Past 1 year",
  "all time": "All time",
} as const;
