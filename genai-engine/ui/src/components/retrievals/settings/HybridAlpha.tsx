import React from "react";

interface HybridAlphaProps {
  alpha: number;
  onChange: (alpha: number) => void;
  isExecuting: boolean;
}

export const HybridAlpha: React.FC<HybridAlphaProps> = React.memo(({ alpha, onChange, isExecuting }) => {
  const handleAlphaChange = (value: number): void => {
    onChange(Math.max(0, Math.min(1, value)));
  };

  return (
    <div>
      <label htmlFor="alpha" className="block text-sm font-medium text-gray-900 mb-2">
        Hybrid Alpha
      </label>
      <div className="flex items-center space-x-3">
        <input
          type="range"
          id="alpha"
          min="0"
          max="1"
          step="0.01"
          value={alpha}
          onChange={(e) => handleAlphaChange(parseFloat(e.target.value))}
          className="flex-1"
          disabled={isExecuting}
        />
        <span className="text-sm text-gray-600 w-12">{alpha.toFixed(2)}</span>
      </div>
      <p className="mt-1 text-xs text-gray-500">Balance between vector search (0) and keyword search (1)</p>
    </div>
  );
});
