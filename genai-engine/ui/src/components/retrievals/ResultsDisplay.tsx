import React, { useState } from "react";

import type { SearchMethod } from "./types";

import { SCORE_THRESHOLDS } from "@/constants/search";
import type { WeaviateQueryResults } from "@/lib/api-client/api-client";
import { extractVectorArray, formatVectorPreview, getVectorStats } from "@/lib/vector-utils";

interface ResultsDisplayProps {
  results: WeaviateQueryResults | null;
  isLoading: boolean;
  error: string | null;
  query: string;
  searchMethod: SearchMethod;
}

export const ResultsDisplay: React.FC<ResultsDisplayProps> = React.memo(({ results, isLoading, error, query, searchMethod }) => {
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  const toggleExpanded = (resultId: string) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(resultId)) {
      newExpanded.delete(resultId);
    } else {
      newExpanded.add(resultId);
    }
    setExpandedResults(newExpanded);
  };

  const formatValue = (value: unknown): string => {
    try {
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
    } catch {
      return "[Error formatting value]";
    }
  };

  const getScoreColor = (score: number | null | undefined, searchMethod: SearchMethod): string => {
    if (score === undefined || score === null) return "text-gray-500";

    if (searchMethod === "nearText") {
      // For distance: lower is better
      if (score < SCORE_THRESHOLDS.nearText.good) return "text-green-600";
      if (score < SCORE_THRESHOLDS.nearText.medium) return "text-yellow-600";
      return "text-red-600";
    } else {
      // For BM25/hybrid: higher is better
      if (score > SCORE_THRESHOLDS.bm25.good) return "text-green-600";
      if (score > SCORE_THRESHOLDS.bm25.medium) return "text-yellow-600";
      return "text-red-600";
    }
  };

  const getScoreLabel = (searchMethod: SearchMethod): string => {
    switch (searchMethod) {
      case "nearText":
        return "Distance";
      case "bm25":
        return "BM25 Score";
      case "hybrid":
        return "Hybrid Score";
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
            <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
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
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No results yet</h3>
          <p className="mt-1 text-sm text-gray-600">Execute a search query to see results here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {query && (
        <div className="mb-4 p-3 bg-gray-50 rounded-md">
          <div className="text-sm">
            <span className="font-medium text-gray-900">Query:</span>
            <span className="ml-2 text-gray-600">&quot;{query}&quot;</span>
          </div>
          <div className="text-sm mt-1">
            <span className="font-medium text-gray-900">Method:</span>
            <span className="ml-2 text-gray-600 capitalize">{searchMethod}</span>
          </div>
          <div className="text-sm mt-1">
            <span className="font-medium text-gray-900">Results:</span>
            <span className="ml-2 text-gray-600">{results.objects.length} results</span>
          </div>
        </div>
      )}

      {results.objects.length === 0 ? (
        <div className="text-center py-8">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.29-1.009-5.824-2.709M15 6.708A7.962 7.962 0 0112 5c-2.34 0-4.29 1.009-5.824 2.709"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
          <p className="mt-1 text-sm text-gray-600">Try adjusting your search query or settings.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {results.objects.map((result, index) => {
            // Defensive checks for malformed data
            if (!result || typeof result !== "object") {
              return null;
            }

            const resultId = result.uuid || `result-${index}`;
            const isExpanded = expandedResults.has(resultId);
            const { _additional, ...properties } = result.properties || {};

            return (
              <div key={resultId} className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="p-4 cursor-pointer hover:bg-gray-50 transition-colors duration-200" onClick={() => toggleExpanded(result.uuid)}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          #{index + 1}
                        </span>
                        <span className="text-sm text-gray-500">ID: {result.uuid}</span>
                      </div>

                      {/* Show first few properties as preview */}
                      <div className="space-y-1">
                        {properties &&
                          Object.entries(properties)
                            .slice(0, 3)
                            .map(([key, value]) => (
                              <div key={key} className="text-sm">
                                <span className="font-medium text-gray-900">{key}:</span>
                                <span className="ml-2 text-gray-600">{formatValue(value)}</span>
                              </div>
                            ))}
                        {properties && Object.keys(properties).length > 3 && (
                          <div className="text-sm text-gray-500">+{Object.keys(properties).length - 3} more properties</div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      {result.metadata && (result.metadata.distance !== undefined || result.metadata.score !== undefined) && (
                        <div className="text-right">
                          <div className="text-xs text-gray-500">{getScoreLabel(searchMethod)}</div>
                          <div
                            className={`text-sm font-medium ${getScoreColor(
                              searchMethod === "nearText" ? result.metadata.distance : result.metadata.score,
                              searchMethod === "nearText" ? "nearText" : "bm25"
                            )}`}
                          >
                            {(() => {
                              if (searchMethod === "nearText") {
                                return typeof result.metadata?.distance === "number" ? result.metadata.distance.toFixed(4) : "N/A";
                              } else {
                                const score = result.metadata?.score;
                                if (typeof score === "number") {
                                  return score.toFixed(4);
                                } else if (typeof score === "string" && score !== null && score !== undefined) {
                                  return parseFloat(score).toFixed(4);
                                } else {
                                  return "N/A";
                                }
                              }
                            })()}
                          </div>
                        </div>
                      )}

                      <svg
                        className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-gray-200 bg-gray-50 p-4">
                    <div className="space-y-4">
                      {properties && Object.keys(properties).length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-2">Properties</h4>
                          <div className="bg-white rounded border p-3">
                            <pre className="text-xs text-gray-600 overflow-x-auto">{JSON.stringify(properties, null, 2)}</pre>
                          </div>
                        </div>
                      )}

                      {result.metadata && (
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 mb-2">Metadata</h4>
                          <div className="bg-white rounded border p-3">
                            <div className="space-y-2 text-sm">
                              {result.metadata.distance !== undefined && (
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Distance:</span>
                                  <span className={`font-medium ${getScoreColor(result.metadata.distance, "nearText")}`}>
                                    {typeof result.metadata.distance === "number"
                                      ? result.metadata.distance.toFixed(6)
                                      : (result.metadata.distance ?? "N/A")}
                                  </span>
                                </div>
                              )}
                              {result.metadata.certainty !== undefined && result.metadata.certainty !== null && (
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Certainty:</span>
                                  <span className={`font-medium ${getScoreColor(1 - (result.metadata.certainty || 0), "nearText")}`}>
                                    {typeof result.metadata.certainty === "number" ? result.metadata.certainty.toFixed(6) : "N/A"}
                                  </span>
                                </div>
                              )}
                              {result.metadata.score !== undefined && result.metadata.score !== null && result.metadata.score !== 0 && (
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Score:</span>
                                  <span className={`font-medium ${getScoreColor(result.metadata.score, "bm25")}`}>
                                    {(() => {
                                      const score = result.metadata.score;
                                      if (typeof score === "number") {
                                        return score.toFixed(6);
                                      } else if (typeof score === "string" && score !== null && score !== undefined) {
                                        return parseFloat(score).toFixed(6);
                                      } else {
                                        return "N/A";
                                      }
                                    })()}
                                  </span>
                                </div>
                              )}
                              {result.metadata.explain_score && (
                                <div>
                                  <span className="text-gray-600">Explain Score:</span>
                                  <div className="mt-1 text-xs text-gray-500 bg-gray-100 p-2 rounded">{result.metadata.explain_score}</div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}

                      {(() => {
                        const vectorArray = extractVectorArray(result.vector);
                        if (!vectorArray) return null;

                        const stats = getVectorStats(vectorArray);

                        return (
                          <div>
                            <h4 className="text-sm font-medium text-gray-900 mb-2">Vector Embedding ({vectorArray.length} dimensions)</h4>
                            <div className="bg-white rounded border p-3">
                              <div className="text-xs text-gray-600">
                                <div className="mb-2">First 10 dimensions: {formatVectorPreview(vectorArray, 10)}</div>
                                {stats && (
                                  <div className="text-gray-500">
                                    Min: {stats.min.toFixed(4)}, Max: {stats.max.toFixed(4)}, Mean: {stats.mean.toFixed(4)}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })()}
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
});
