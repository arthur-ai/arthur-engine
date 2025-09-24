"use client";

import React, { useState } from "react";
import { WeaviateCollection } from "@/lib/weaviate-client";

interface QueryInterfaceProps {
  selectedCollection: WeaviateCollection | null;
  onExecuteQuery: (query: string, searchMethod: string) => void;
  isExecuting: boolean;
}

export const QueryInterface: React.FC<QueryInterfaceProps> = ({
  selectedCollection,
  onExecuteQuery,
  isExecuting,
}) => {
  const [query, setQuery] = useState("");
  const [searchMethod, setSearchMethod] = useState<
    "nearText" | "bm25" | "hybrid"
  >("nearText");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && selectedCollection) {
      onExecuteQuery(query.trim(), searchMethod);
    }
  };

  const handleClear = () => {
    setQuery("");
  };

  const isDisabled = !selectedCollection || !query.trim() || isExecuting;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Query Interface
      </h3>

      {!selectedCollection ? (
        <div className="text-center py-8">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No collection selected
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Please select a collection from the list above to start querying.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="searchMethod"
              className="block text-sm font-medium text-gray-900 mb-2 !text-gray-900"
            >
              Search Method
            </label>
            <select
              id="searchMethod"
              value={searchMethod}
              onChange={(e) =>
                setSearchMethod(
                  e.target.value as "nearText" | "bm25" | "hybrid"
                )
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 !text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              disabled={isExecuting}
            >
              <option value="nearText">Near Text (Vector Search)</option>
              <option value="bm25">BM25 (Keyword Search)</option>
              <option value="hybrid">Hybrid (Vector + Keyword)</option>
            </select>
            <div className="mt-1 text-xs text-gray-500">
              {searchMethod === "nearText" &&
                "Semantic search using vector similarity"}
              {searchMethod === "bm25" && "Traditional keyword-based search"}
              {searchMethod === "hybrid" &&
                "Combines vector and keyword search for best results"}
            </div>
          </div>

          <div>
            <label
              htmlFor="query"
              className="block text-sm font-medium text-gray-900 mb-2 !text-gray-900"
            >
              Query Text
            </label>
            <textarea
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 !text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              disabled={isExecuting}
            />
            <div className="mt-1 flex justify-between items-center">
              <span className="text-xs text-gray-500">
                {query.length} characters
              </span>
              {query && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-xs text-gray-500 hover:text-gray-700"
                  disabled={isExecuting}
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Collection:</span>{" "}
              {selectedCollection.name}
            </div>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={handleClear}
                disabled={isExecuting || !query}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-900 !text-gray-900 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clear
              </button>
              <button
                type="submit"
                disabled={isDisabled}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isExecuting ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Searching...
                  </>
                ) : (
                  <>
                    <svg
                      className="h-4 w-4 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                      />
                    </svg>
                    Search
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
};
