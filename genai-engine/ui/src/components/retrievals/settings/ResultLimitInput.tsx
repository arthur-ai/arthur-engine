import React, { useState } from "react";

interface ResultLimitInputProps {
  limit: number;
  onChange: (limit: number) => void;
  isExecuting: boolean;
}

export const ResultLimitInput: React.FC<ResultLimitInputProps> = React.memo(({ limit, onChange, isExecuting }) => {
  const [limitInput, setLimitInput] = useState(limit.toString());

  const handleLimitInputChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setLimitInput(e.target.value);
  };

  const handleLimitBlur = (e: React.FocusEvent<HTMLInputElement>): void => {
    const value = e.target.value;
    const numValue = parseInt(value);
    if (isNaN(numValue) || value === "") {
      onChange(1);
      setLimitInput("1");
    } else {
      const clampedValue = Math.max(1, Math.min(100, numValue));
      onChange(clampedValue);
      setLimitInput(clampedValue.toString());
    }
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
        value={limitInput}
        onChange={handleLimitInputChange}
        onBlur={handleLimitBlur}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        disabled={isExecuting}
      />
      <p className="mt-1 text-xs text-gray-500">Maximum number of results to return (1-100)</p>
    </div>
  );
});
