import React from "react";

import { SearchSliderField } from "./SearchSliderField";

interface DistanceThresholdProps {
  distance: number;
  onChange: (distance: number) => void;
  isExecuting: boolean;
}

export const DistanceThreshold: React.FC<DistanceThresholdProps> = React.memo(({ distance, onChange, isExecuting }) => {
  return (
    <SearchSliderField
      label="Distance Threshold"
      helperText="Maximum distance for vector similarity (0 = exact match, 1 = any match)"
      value={distance}
      onChange={onChange}
      disabled={isExecuting}
      formatValue={(value) => value.toFixed(2)}
    />
  );
});
