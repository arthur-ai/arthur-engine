import React from "react";

interface DistanceThresholdProps {
  distance: number;
  onChange: (distance: number) => void;
  isExecuting: boolean;
}

export const DistanceThreshold: React.FC<DistanceThresholdProps> = React.memo(({ distance, onChange, isExecuting }) => {
  const handleDistanceChange = (value: number): void => {
    onChange(Math.max(0, Math.min(1, value)));
  };

  return (
    <div>
      <label htmlFor="distance" className="block text-sm font-medium text-gray-900 mb-2">
        Distance Threshold
      </label>
      <div className="flex items-center space-x-3">
        <input
          type="range"
          id="distance"
          min="0"
          max="1"
          step="0.01"
          value={distance}
          onChange={(e) => handleDistanceChange(parseFloat(e.target.value))}
          className="flex-1"
          disabled={isExecuting}
        />
        <span className="text-sm text-gray-600 w-12">{distance.toFixed(2)}</span>
      </div>
      <p className="mt-1 text-xs text-gray-500">Maximum distance for vector similarity (0 = exact match, 1 = any match)</p>
    </div>
  );
});
