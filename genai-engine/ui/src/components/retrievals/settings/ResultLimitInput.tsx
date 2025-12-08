import React from "react";

interface ResultLimitInputProps {
  limit: number;
  onChange: (limit: number) => void;
  isExecuting: boolean;
}

export const ResultLimitInput: React.FC<ResultLimitInputProps> = React.memo(({ limit, onChange, isExecuting }) => {
  const handleLimitChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const value = e.target.value;
    const numValue = parseInt(value);

    if (value === "" || isNaN(numValue)) {
      return;
    }

    const clampedValue = Math.max(1, Math.min(100, numValue));
    onChange(clampedValue);
  };

  return (
    <div>
      <label htmlFor="limit" className="block text-sm font-medium text-gray-900 mb-2">
        Result Limit
      </label>
      <input
        type="number"
        id="limit"
        min="1"
        max="100"
        value={limit}
        onChange={handleLimitChange}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        disabled={isExecuting}
      />
      <p className="mt-1 text-xs text-gray-500">Maximum number of results to return (1-100)</p>
    </div>
  );
});
