"use client";

import React from "react";
import { SearchSettings } from "@/lib/weaviate-client";

interface SettingsPanelProps {
  settings: SearchSettings;
  onSettingsChange: (settings: SearchSettings) => void;
  searchMethod: string;
  isExecuting: boolean;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  onSettingsChange,
  searchMethod,
  isExecuting,
}) => {
  const handleLimitChange = (value: number) => {
    onSettingsChange({
      ...settings,
      limit: Math.max(1, Math.min(100, value)),
    });
  };

  const handleDistanceChange = (value: number) => {
    onSettingsChange({
      ...settings,
      distance: Math.max(0, Math.min(1, value)),
    });
  };

  const handleAlphaChange = (value: number) => {
    onSettingsChange({
      ...settings,
      alpha: Math.max(0, Math.min(1, value)),
    });
  };

  const handleIncludeVectorChange = (checked: boolean) => {
    onSettingsChange({
      ...settings,
      includeVector: checked,
    });
  };

  const handleIncludeMetadataChange = (checked: boolean) => {
    onSettingsChange({
      ...settings,
      includeMetadata: checked,
    });
  };

  const resetToDefaults = () => {
    onSettingsChange({
      limit: 10,
      distance: 0.7,
      alpha: 0.5,
      includeVector: false,
      includeMetadata: true,
    });
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Search Settings</h3>
        <button
          onClick={resetToDefaults}
          disabled={isExecuting}
          className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reset to defaults
        </button>
      </div>

      <div className="space-y-6">
        {/* Limit */}
        <div>
          <label
            htmlFor="limit"
            className="block text-sm font-medium text-gray-700 mb-2"
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
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            disabled={isExecuting}
          />
          <p className="mt-1 text-xs text-gray-500">
            Maximum number of results to return (1-100)
          </p>
        </div>

        {/* Distance (for vector search) */}
        {(searchMethod === "nearText" || searchMethod === "hybrid") && (
          <div>
            <label
              htmlFor="distance"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Distance Threshold
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                id="distance"
                min="0"
                max="1"
                step="0.01"
                value={settings.distance}
                onChange={(e) =>
                  handleDistanceChange(parseFloat(e.target.value))
                }
                className="flex-1"
                disabled={isExecuting}
              />
              <span className="text-sm text-gray-600 w-12">
                {settings.distance.toFixed(2)}
              </span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Maximum distance for vector similarity (0 = exact match, 1 = any
              match)
            </p>
          </div>
        )}

        {/* Alpha (for hybrid search) */}
        {searchMethod === "hybrid" && (
          <div>
            <label
              htmlFor="alpha"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Hybrid Alpha
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                id="alpha"
                min="0"
                max="1"
                step="0.01"
                value={settings.alpha || 0.5}
                onChange={(e) => handleAlphaChange(parseFloat(e.target.value))}
                className="flex-1"
                disabled={isExecuting}
              />
              <span className="text-sm text-gray-600 w-12">
                {(settings.alpha || 0.5).toFixed(2)}
              </span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Balance between vector search (0) and keyword search (1)
            </p>
          </div>
        )}

        {/* Include Options */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-700">
            Include in Results
          </h4>

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
              className="ml-2 text-sm text-gray-700"
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
              className="ml-2 text-sm text-gray-700"
            >
              Vector embeddings
            </label>
          </div>
        </div>

        {/* Search Method Info */}
        <div className="bg-gray-50 rounded-md p-3">
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Current Search Method
          </h4>
          <div className="text-sm text-gray-600">
            {searchMethod === "nearText" && (
              <p>
                <strong>Near Text:</strong> Semantic search using vector
                similarity. Results are ranked by how similar their meaning is
                to your query.
              </p>
            )}
            {searchMethod === "bm25" && (
              <p>
                <strong>BM25:</strong> Traditional keyword-based search. Results
                are ranked by keyword frequency and document length.
              </p>
            )}
            {searchMethod === "hybrid" && (
              <p>
                <strong>Hybrid:</strong> Combines vector and keyword search.
                Alpha controls the balance: 0 = pure vector, 1 = pure keyword.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
