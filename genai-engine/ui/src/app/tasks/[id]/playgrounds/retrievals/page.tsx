"use client";

import React, { useState, useEffect } from "react";
import { ConnectionForm } from "@/components/weaviate/ConnectionForm";
import { QueryConfiguration } from "@/components/weaviate/QueryConfiguration";
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
  const [connectionUrl, setConnectionUrl] = useState<string>("");

  // Auto-connect on page load if saved credentials exist
  useEffect(() => {
    const autoConnect = async () => {
      const savedUrl = localStorage.getItem("weaviate-url");
      const savedApiKey = localStorage.getItem("weaviate-api-key");

      if (savedUrl && savedApiKey) {
        setIsConnecting(true);
        try {
          const success = await weaviateService.connect({
            url: savedUrl,
            apiKey: savedApiKey,
          });
          setIsConnected(success);
          if (success) {
            setConnectionUrl(savedUrl);
          } else {
            // Clear invalid credentials
            localStorage.removeItem("weaviate-url");
            localStorage.removeItem("weaviate-api-key");
          }
        } catch (err) {
          console.error("Auto-connect failed:", err);
          // Clear invalid credentials
          localStorage.removeItem("weaviate-url");
          localStorage.removeItem("weaviate-api-key");
        } finally {
          setIsConnecting(false);
        }
      }
    };

    autoConnect();
  }, []);

  const handleConnect = async (
    connection: WeaviateConnection
  ): Promise<boolean> => {
    setIsConnecting(true);
    setError(null);

    try {
      const success = await weaviateService.connect(connection);
      setIsConnected(success);
      if (success) {
        setConnectionUrl(connection.url);
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
    setConnectionUrl("");
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
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white shadow flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between space-y-4 lg:space-y-0">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  Weaviate Retrievals Playground
                </h1>
                <p className="text-gray-600 mt-2">
                  Test and experiment with different vector retrieval strategies
                  and configurations.
                </p>
              </div>

              {/* Connection Status */}
              {isConnected && (
                <div className="flex items-center space-x-3 bg-green-50 border border-green-200 rounded-lg px-4 py-3 self-start">
                  <div className="flex items-center">
                    <svg
                      className="h-5 w-5 text-green-500 mr-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <div>
                      <div className="text-sm font-medium text-green-800">
                        Connected to Weaviate
                      </div>
                      <div className="text-xs text-green-600">
                        {connectionUrl}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={handleDisconnect}
                    className="inline-flex items-center px-3 py-1.5 border border-green-300 shadow-sm text-xs font-medium rounded-md text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    <svg
                      className="h-3 w-3 mr-1"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                      />
                    </svg>
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full px-4 sm:px-6 lg:px-8">
          <div className="h-full py-6">
            {!isConnected ? (
              /* Centered Connection Form at Top */
              <div className="flex justify-center pt-12">
                <div className="w-full max-w-md">
                  <ConnectionForm
                    onConnect={handleConnect}
                    isConnecting={isConnecting}
                    isConnected={isConnected}
                    onDisconnect={handleDisconnect}
                  />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-[600px_1fr] gap-6 h-full">
                {/* Left Column - Collections, Query Interface, and Settings */}
                <div className="space-y-6 lg:sticky lg:top-0 lg:max-h-[calc(100vh-16rem)] lg:overflow-y-auto">
                  {isConnecting ? (
                    <div className="bg-white rounded-lg shadow p-6">
                      <div className="text-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <h3 className="text-sm font-medium text-gray-900">
                          Connecting to Weaviate...
                        </h3>
                        <p className="mt-1 text-sm text-gray-600">
                          Attempting to reconnect with saved credentials.
                        </p>
                      </div>
                    </div>
                  ) : isConnected ? (
                    <>
                      <div>
                        <h2 className="text-lg font-medium text-gray-900 mb-4 text-center">
                          Query Configuration
                        </h2>
                      </div>
                      <QueryConfiguration
                        selectedCollection={selectedCollection}
                        onCollectionSelect={handleCollectionSelect}
                        onExecuteQuery={handleExecuteQuery}
                        isExecuting={isExecuting}
                        searchMethod={searchMethod}
                        onSearchMethodChange={setSearchMethod}
                        settings={settings}
                        onSettingsChange={handleSettingsChange}
                      />
                    </>
                  ) : null}
                </div>

                {/* Right Column - Results Display */}
                <div className="space-y-6 lg:max-h-[calc(100vh-16rem)] lg:overflow-y-auto">
                  {isConnected && (
                    <div>
                      <h2 className="text-lg font-medium text-gray-900 mb-4 text-center">
                        Search Results
                      </h2>
                    </div>
                  )}

                  {isConnected && (
                    <ResultsDisplay
                      results={results}
                      isLoading={isExecuting}
                      error={error}
                      query={query}
                      searchMethod={searchMethod}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
