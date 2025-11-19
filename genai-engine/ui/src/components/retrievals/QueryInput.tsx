import React from "react";

interface QueryInputProps {
  query: string;
  onQueryChange: (query: string) => void;
  onClear: () => void;
  isExecuting: boolean;
}

export const QueryInput: React.FC<QueryInputProps> = ({ query, onQueryChange, onClear, isExecuting }) => {
  return (
    <div>
      <label htmlFor="query" className="block text-sm font-medium text-gray-900 mb-2">
        Query Text
      </label>
      <textarea
        id="query"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="Enter your search query..."
        rows={3}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        disabled={isExecuting}
        aria-label="Search query text"
        aria-describedby="query-help"
      />
      <div className="mt-1 flex justify-between items-center">
        <span id="query-help" className="text-xs text-gray-500">
          {query.length} characters
        </span>
        {query && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-gray-500 hover:text-gray-700"
            disabled={isExecuting}
            aria-label="Clear search query"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
};
