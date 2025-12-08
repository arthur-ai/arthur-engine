import React from "react";

import { SearchSliderField } from "./SearchSliderField";

interface HybridAlphaProps {
  alpha: number;
  onChange: (alpha: number) => void;
  isExecuting: boolean;
}

export const HybridAlpha: React.FC<HybridAlphaProps> = React.memo(({ alpha, onChange, isExecuting }) => {
  return (
    <SearchSliderField
      label="Hybrid Alpha"
      helperText="Balance between vector search (0) and keyword search (1)"
      value={alpha}
      onChange={onChange}
      disabled={isExecuting}
      formatValue={(value) => value.toFixed(2)}
    />
  );
});
