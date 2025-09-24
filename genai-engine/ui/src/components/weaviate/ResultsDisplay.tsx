"use client";

import React, { useState } from "react";
import { QueryResult, SearchResult } from "@/lib/weaviate-client";

interface ResultsDisplayProps {
  results: QueryResult | null;
  isLoading: boolean;
  error: string | null;
  query: string;
  searchMethod: string;
}

export const ResultsDisplay: React.FC<ResultsDisplayProps> = ({
  results,
  isLoading,
  error,
  query,
  searchMethod,
}) => {
  const [expandedResults, setExpandedResults] = useState<Set<string>>(
    new Set()
  );

  const toggleExpanded = (resultId: string) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(resultId)) {
      newExpanded.delete(resultId);
    } else {
      newExpanded.add(resultId);
    }
    setExpandedResults(newExpanded);
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) {
      return "null";
    }
    if (typeof value === "object") {
      return JSON.stringify(value, null, 2);
    }
    if (typeof value === "string" && value.length > 100) {
      return value.substring(0, 100) + "...";
    }
    return String(value);
  };

  const getScoreColor = (
    score: number | undefined,
    searchMethod: string
  ): string => {
    if (score === undefined) return "text-gray-500";

    if (searchMethod === "nearText") {
      // For vector search, lower distance is better
      if (score < 0.3) return "text-green-600";
      if (score < 0.6) return "text-yellow-600";
      return "text-red-600";
    } else {
      // For BM25 and hybrid (when showing score), higher score is better
      if (score > 0.7) return "text-green-600";
      if (score > 0.4) return "text-yellow-600";
      return "text-red-600";
    }
  };

  const getScoreLabel = (searchMethod: string): string => {
    switch (searchMethod) {
      case "nearText":
        return "Distance";
      case "bm25":
        return "BM25 Score";
      case "hybrid":
        return "Hybrid Score";
      default:
        return "Score";
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Search Error</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
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
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No results yet
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Execute a search query to see results here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {query && (
        <div className="mb-4 p-3 bg-gray-50 rounded-md">
          <div className="text-sm">
            <span className="font-medium text-gray-900 !text-gray-900">
              Query:
            </span>
            <span className="ml-2 text-gray-600">"{query}"</span>
          </div>
          <div className="text-sm mt-1">
            <span className="font-medium text-gray-900 !text-gray-900">
              Method:
            </span>
            <span className="ml-2 text-gray-600 capitalize">
              {searchMethod}
            </span>
          </div>
          <div className="text-sm mt-1">
            <span className="font-medium text-gray-900 !text-gray-900">
              Results:
            </span>
            <span className="ml-2 text-gray-600">
              {results.totalResults} results in {results.queryTime}ms
            </span>
          </div>
        </div>
      )}

      {results.results.length === 0 ? (
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
              d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.29-1.009-5.824-2.709M15 6.708A7.962 7.962 0 0112 5c-2.34 0-4.29 1.009-5.824 2.709"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No results found
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            Try adjusting your search query or settings.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {results.results.map((result, index) => {
            const isExpanded = expandedResults.has(result.id);
            const { _additional, ...properties } = result.properties;

            return (
              <div
                key={result.id}
                className="border border-gray-200 rounded-lg overflow-hidden"
              >
                <div
                  className="p-4 cursor-pointer hover:bg-gray-50 transition-colors duration-200"
                  onClick={() => toggleExpanded(result.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          #{index + 1}
                        </span>
                        <span className="text-sm text-gray-500">
                          ID: {result.id}
                        </span>
                      </div>

                      {/* Show first few properties as preview */}
                      <div className="space-y-1">
                        {Object.entries(properties)
                          .slice(0, 3)
                          .map(([key, value]) => (
                            <div key={key} className="text-sm">
                              <span className="font-medium text-gray-900 !text-gray-900">
                                {key}:
                              </span>
                              <span className="ml-2 text-gray-600">
                                {formatValue(value)}
                              </span>
                            </div>
                          ))}
                        {Object.keys(properties).length > 3 && (
                          <div className="text-sm text-gray-500">
                            +{Object.keys(properties).length - 3} more
                            properties
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      {/* Score/Distance */}
                      {(result.metadata.distance !== undefined ||
                        result.metadata.score !== undefined) && (
                        <div className="text-right">
                          <div className="text-xs text-gray-500">
                            {getScoreLabel(searchMethod)}
                          </div>
                          <div
                            className={`text-sm font-medium ${getScoreColor(
                              searchMethod === "nearText"
                                ? result.metadata.distance
                                : result.metadata.score,
                              searchMethod === "nearText" ? "nearText" : "bm25"
                            )}`}
                          >
                            {(() => {
                              // For nearText, show distance; for BM25/hybrid, show score
                              if (searchMethod === "nearText") {
                                return typeof result.metadata.distance ===
                                  "number"
                                  ? result.metadata.distance.toFixed(4)
                                  : "N/A";
                              } else {
                                // Handle both number and string scores
                                const score = result.metadata.score;
                                if (typeof score === "number") {
                                  return score.toFixed(4);
                                } else if (
                                  typeof score === "string" &&
                                  score !== null &&
                                  score !== undefined
                                ) {
                                  return parseFloat(score).toFixed(4);
                                } else {
                                  return "N/A";
                                }
                              }
                            })()}
                          </div>
                        </div>
                      )}

                      {/* Expand/Collapse button */}
                      <svg
                        className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${
                          isExpanded ? "rotate-180" : ""
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="border-t border-gray-200 bg-gray-50 p-4">
                    <div className="space-y-4">
                      {/* Properties */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-2 !text-gray-900">
                          Properties
                        </h4>
                        <div className="bg-white rounded border p-3">
                          <pre className="text-xs text-gray-600 overflow-x-auto">
                            {JSON.stringify(properties, null, 2)}
                          </pre>
                        </div>
                      </div>

                      {/* Metadata */}
                      {result.metadata && (
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-2 !text-gray-900">
                            Metadata
                          </h4>
                          <div className="bg-white rounded border p-3">
                            <div className="space-y-2 text-sm">
                              {result.metadata.distance !== undefined && (
                                <div className="flex justify-between">
                                  <span className="text-gray-600">
                                    Distance:
                                  </span>
                                  <span
                                    className={`font-medium ${getScoreColor(
                                      result.metadata.distance,
                                      "nearText"
                                    )}`}
                                  >
                                    {typeof result.metadata.distance ===
                                    "number"
                                      ? result.metadata.distance.toFixed(6)
                                      : result.metadata.distance ?? "N/A"}
                                  </span>
                                </div>
                              )}
                              {result.metadata.score !== undefined && (
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Score:</span>
                                  <span
                                    className={`font-medium ${getScoreColor(
                                      result.metadata.score,
                                      "bm25"
                                    )}`}
                                  >
                                    {(() => {
                                      const score = result.metadata.score;
                                      if (typeof score === "number") {
                                        return score.toFixed(6);
                                      } else if (
                                        typeof score === "string" &&
                                        score !== null &&
                                        score !== undefined
                                      ) {
                                        return parseFloat(score).toFixed(6);
                                      } else {
                                        return "N/A";
                                      }
                                    })()}
                                  </span>
                                </div>
                              )}
                              {result.metadata.explainScore && (
                                <div>
                                  <span className="text-gray-600">
                                    Explain Score:
                                  </span>
                                  <div className="mt-1 text-xs text-gray-500 bg-gray-100 p-2 rounded">
                                    {result.metadata.explainScore}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Vector (if included) */}
                      {result.vector && (
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-2 !text-gray-900">
                            Vector Embedding ({result.vector.length} dimensions)
                          </h4>
                          <div className="bg-white rounded border p-3">
                            <div className="text-xs text-gray-600">
                              <div className="mb-2">
                                First 10 dimensions: [
                                {result.vector
                                  .slice(0, 10)
                                  .map((v) =>
                                    typeof v === "number"
                                      ? v.toFixed(4)
                                      : v ?? "N/A"
                                  )
                                  .join(", ")}
                                ...]
                              </div>
                              <div className="text-gray-500">
                                Min:{" "}
                                {result.vector.length > 0
                                  ? Math.min(...result.vector).toFixed(4)
                                  : "N/A"}
                                , Max:{" "}
                                {result.vector.length > 0
                                  ? Math.max(...result.vector).toFixed(4)
                                  : "N/A"}
                                , Mean:{" "}
                                {result.vector.length > 0
                                  ? (
                                      result.vector.reduce((a, b) => a + b, 0) /
                                      result.vector.length
                                    ).toFixed(4)
                                  : "N/A"}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
