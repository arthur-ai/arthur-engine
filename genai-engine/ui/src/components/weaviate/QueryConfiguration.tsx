"use client";

import React, { useState, useEffect } from "react";
import {
  WeaviateCollection,
  weaviateService,
  SearchSettings,
} from "@/lib/weaviate-client";

interface QueryConfigurationProps {
  selectedCollection: WeaviateCollection | null;
  onCollectionSelect: (collection: WeaviateCollection | null) => void;
  onExecuteQuery: (query: string, searchMethod: string) => void;
  isExecuting: boolean;
  searchMethod: "nearText" | "bm25" | "hybrid";
  onSearchMethodChange: (method: "nearText" | "bm25" | "hybrid") => void;
  settings: SearchSettings;
  onSettingsChange: (settings: SearchSettings) => void;
}

export const QueryConfiguration: React.FC<QueryConfigurationProps> = ({
  selectedCollection,
  onCollectionSelect,
  onExecuteQuery,
  isExecuting,
  searchMethod,
  onSearchMethodChange,
  settings,
  onSettingsChange,
}) => {
  const [collections, setCollections] = useState<WeaviateCollection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Record<string, any>>({});
  const [query, setQuery] = useState("");

  const fetchCollections = async () => {
    if (!weaviateService.isConnected()) {
      setError("Not connected to Weaviate");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const fetchedCollections = await weaviateService.getCollections();
      setCollections(fetchedCollections);

      // Fetch stats for each collection
      const statsPromises = fetchedCollections.map(async (collection) => {
        try {
          const stats = await weaviateService.getCollectionStats(
            collection.name
          );
          return { [collection.name]: stats };
        } catch (err) {
          console.warn(
            `Failed to get stats for collection ${collection.name}:`,
            err
          );
          return {
            [collection.name]: {
              totalObjects: 0,
              vectorizer: "unknown",
              properties: 0,
            },
          };
        }
      });

      const statsResults = await Promise.all(statsPromises);
      const combinedStats = statsResults.reduce(
        (acc, curr) => ({ ...acc, ...curr }),
        {}
      );
      setStats(combinedStats);
    } catch (err) {
      console.error("Failed to fetch collections:", err);
      setError("Failed to load collections. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCollections();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && selectedCollection) {
      onExecuteQuery(query.trim(), searchMethod);
    }
  };

  const handleClear = () => {
    setQuery("");
  };

  const handleLimitChange = (value: number) => {
    onSettingsChange({
      ...settings,
      limit: Math.max(1, Math.min(100, value)),
    });
  };

  const handleIncludeMetadataChange = (checked: boolean) => {
    onSettingsChange({
      ...settings,
      includeMetadata: checked,
    });
  };

  const handleIncludeVectorChange = (checked: boolean) => {
    onSettingsChange({
      ...settings,
      includeVector: checked,
    });
  };

  const isDisabled = !selectedCollection || !query.trim() || isExecuting;

  const getCollectionDisplayText = (collection: WeaviateCollection) => {
    const collectionStats = stats[collection.name] || {
      totalObjects: 0,
      vectorizer: "unknown",
      properties: 0,
    };

    return `${collection.name} (${collectionStats.totalObjects} objects, ${
      collectionStats.properties
    } properties${
      collectionStats.vectorizer !== "unknown"
        ? `, ${collectionStats.vectorizer}`
        : ""
    })`;
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Query Configuration
      </h3>

      <div className="space-y-4">
        {/* Collection Selector */}
        <div>
          <label
            htmlFor="collection"
            className="block text-sm font-medium text-gray-900 mb-2"
          >
            Collection
          </label>
          <div className="flex items-center space-x-2">
            <select
              id="collection"
              value={selectedCollection?.name || ""}
              onChange={(e) => {
                const collection = collections.find(
                  (c) => c.name === e.target.value
                );
                onCollectionSelect(collection || null);
              }}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              disabled={isExecuting || loading}
            >
              <option value="">
                {loading ? "Loading collections..." : "Select a collection"}
              </option>
              {collections.map((collection) => (
                <option key={collection.name} value={collection.name}>
                  {getCollectionDisplayText(collection)}
                </option>
              ))}
            </select>
            <button
              onClick={fetchCollections}
              disabled={isExecuting || loading}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-900 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          </div>
          {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
        </div>

        {/* Search Method */}
        <div>
          <label
            htmlFor="searchMethod"
            className="block text-sm font-medium text-gray-900 mb-2"
          >
            Search Method
          </label>
          <select
            id="searchMethod"
            value={searchMethod}
            onChange={(e) =>
              onSearchMethodChange(
                e.target.value as "nearText" | "bm25" | "hybrid"
              )
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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

        {/* Query Text */}
        <div>
          <label
            htmlFor="query"
            className="block text-sm font-medium text-gray-900 mb-2"
          >
            Query Text
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your search query..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
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

        {/* Result Limit */}
        <div>
          <label
            htmlFor="limit"
            className="block text-sm font-medium text-gray-900 mb-2"
          >
            Result Limit
          </label>
          <input
            type="number"
            id="limit"
            min="1"
            max="100"
            value={settings.limit}
            onChange={(e) => handleLimitChange(parseInt(e.target.value) || 1)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            disabled={isExecuting}
          />
          <p className="mt-1 text-xs text-gray-500">
            Maximum number of results to return (1-100)
          </p>
        </div>

        {/* Include Options */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-3">
            Include in Results
          </h4>
          <div className="space-y-2">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="includeMetadata"
                checked={settings.includeMetadata}
                onChange={(e) => handleIncludeMetadataChange(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={isExecuting}
              />
              <label
                htmlFor="includeMetadata"
                className="ml-2 text-sm text-gray-900"
              >
                Metadata (distance, score, explainScore)
              </label>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="includeVector"
                checked={settings.includeVector}
                onChange={(e) => handleIncludeVectorChange(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={isExecuting}
              />
              <label
                htmlFor="includeVector"
                className="ml-2 text-sm text-gray-900"
              >
                Vector embeddings
              </label>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end pt-4 border-t border-gray-200">
          <div className="flex space-x-3">
            <button
              type="button"
              onClick={handleClear}
              disabled={isExecuting || !query}
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-900 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Clear
            </button>
            <button
              onClick={handleSubmit}
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
      </div>
    </div>
  );
};
