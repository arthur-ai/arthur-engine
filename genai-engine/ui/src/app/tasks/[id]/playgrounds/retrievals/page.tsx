"use client";

import React, { useState } from "react";
import { ConnectionForm } from "@/components/weaviate/ConnectionForm";
import { CollectionSelector } from "@/components/weaviate/CollectionSelector";
import { QueryInterface } from "@/components/weaviate/QueryInterface";
import { SettingsPanel } from "@/components/weaviate/SettingsPanel";
import { ResultsDisplay } from "@/components/weaviate/ResultsDisplay";
import {
  WeaviateConnection,
  WeaviateCollection,
  SearchSettings,
  QueryResult,
  weaviateService,
} from "@/lib/weaviate-client";

export default function PlaygroundsRetrievalsPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [selectedCollection, setSelectedCollection] =
    useState<WeaviateCollection | null>(null);
  const [query, setQuery] = useState("");
  const [searchMethod, setSearchMethod] = useState<
    "nearText" | "bm25" | "hybrid"
  >("nearText");
  const [settings, setSettings] = useState<SearchSettings>({
    limit: 10,
    distance: 0.7,
    alpha: 0.5,
    includeVector: false,
    includeMetadata: true,
  });
  const [results, setResults] = useState<QueryResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async (
    connection: WeaviateConnection
  ): Promise<boolean> => {
    setIsConnecting(true);
    setError(null);

    try {
      const success = await weaviateService.connect(connection);
      setIsConnected(success);
      if (success) {
        setSelectedCollection(null);
        setResults(null);
        setError(null);
      }
      return success;
    } catch (err) {
      console.error("Connection failed:", err);
      return false;
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = () => {
    weaviateService.disconnect();
    setIsConnected(false);
    setSelectedCollection(null);
    setResults(null);
    setError(null);
  };

  const handleCollectionSelect = (collection: WeaviateCollection | null) => {
    setSelectedCollection(collection);
    setResults(null);
    setError(null);
  };

  const handleExecuteQuery = async (queryText: string, method: string) => {
    if (!selectedCollection) return;

    setIsExecuting(true);
    setError(null);
    setQuery(queryText);
    setSearchMethod(method as "nearText" | "bm25" | "hybrid");

    try {
      const queryResults = await weaviateService.search(
        selectedCollection.name,
        queryText,
        method as "nearText" | "bm25" | "hybrid",
        settings
      );
      setResults(queryResults);
    } catch (err) {
      console.error("Query failed:", err);
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setIsExecuting(false);
    }
  };

  const handleSettingsChange = (newSettings: SearchSettings) => {
    setSettings(newSettings);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <h1 className="text-3xl font-bold text-gray-900">
              Weaviate Retrievals Playground
            </h1>
            <p className="text-gray-600 mt-2">
              Test and experiment with different vector retrieval strategies and
              configurations.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Connection and Collection Selection */}
            <div className="lg:col-span-1 space-y-6">
              <ConnectionForm
                onConnect={handleConnect}
                isConnecting={isConnecting}
                isConnected={isConnected}
                onDisconnect={handleDisconnect}
              />

              {isConnected && (
                <CollectionSelector
                  onCollectionSelect={handleCollectionSelect}
                  selectedCollection={selectedCollection}
                />
              )}
            </div>

            {/* Right Column - Query Interface, Settings, and Results */}
            <div className="lg:col-span-2 space-y-6">
              {isConnected ? (
                <>
                  <QueryInterface
                    selectedCollection={selectedCollection}
                    onExecuteQuery={handleExecuteQuery}
                    isExecuting={isExecuting}
                  />

                  {selectedCollection && (
                    <SettingsPanel
                      settings={settings}
                      onSettingsChange={handleSettingsChange}
                      searchMethod={searchMethod}
                      isExecuting={isExecuting}
                    />
                  )}

                  <ResultsDisplay
                    results={results}
                    isLoading={isExecuting}
                    error={error}
                    query={query}
                    searchMethod={searchMethod}
                  />
                </>
              ) : (
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="text-center py-12">
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
                      Connect to Weaviate
                    </h3>
                    <p className="mt-1 text-sm text-gray-600">
                      Please connect to your Weaviate instance to start
                      experimenting with retrievals.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
