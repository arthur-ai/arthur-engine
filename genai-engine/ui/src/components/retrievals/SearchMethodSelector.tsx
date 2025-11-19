import React from "react";

import type { SearchMethod } from "./types";

interface SearchMethodSelectorProps {
  searchMethod: SearchMethod;
  onSearchMethodChange: (method: SearchMethod) => void;
  isExecuting: boolean;
}

export const SearchMethodSelector: React.FC<SearchMethodSelectorProps> = ({ searchMethod, onSearchMethodChange, isExecuting }) => {
  return (
    <div>
      <label htmlFor="searchMethod" className="block text-sm font-medium text-gray-900 mb-2">
        Search Method
      </label>
      <select
        id="searchMethod"
        value={searchMethod}
        onChange={(e) => onSearchMethodChange(e.target.value as SearchMethod)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        disabled={isExecuting}
      >
        <option value="nearText">Near Text (Vector Search)</option>
        <option value="bm25">BM25 (Keyword Search)</option>
        <option value="hybrid">Hybrid (Vector + Keyword)</option>
      </select>
      <div className="mt-1 text-xs text-gray-500">
        {searchMethod === "nearText" && "Semantic search using vector similarity"}
        {searchMethod === "bm25" && "Traditional keyword-based search"}
        {searchMethod === "hybrid" && "Combines vector and keyword search for best results"}
      </div>
    </div>
  );
};

