import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { ConnectionForm, QueryConfiguration, ResultsDisplay } from "./index";
import {
  WeaviateCollection,
  weaviateService,
  SearchSettings,
} from "../../lib/weaviate-client";

export const WeaviateRetrievalsPlayground: React.FC = () => {
  const { id: taskId } = useParams<{ id: string }>();
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
    includeMetadata: true,
    includeVector: false,
  });
  const [results, setResults] = useState<any>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionUrl, setConnectionUrl] = useState<string>("");

  // Auto-connect on page load
  useEffect(() => {
    const savedUrl = localStorage.getItem("weaviate-url");
    const savedApiKey = localStorage.getItem("weaviate-api-key");

    if (savedUrl && savedApiKey) {
      setConnectionUrl(savedUrl);
      setIsConnecting(true);
      weaviateService
        .connect({ url: savedUrl, apiKey: savedApiKey })
        .then(() => {
          setIsConnected(true);
          setIsConnecting(false);
        })
        .catch((err) => {
          console.error("Auto-connect failed:", err);
          setIsConnecting(false);
        });
    }
  }, []);

  const handleConnect = async (url: string, apiKey: string) => {
    setIsConnecting(true);
    setError(null);

    try {
      await weaviateService.connect({ url, apiKey });
      setIsConnected(true);
      setConnectionUrl(url);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to connect to Weaviate"
      );
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
    setConnectionUrl("");
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

    try {
      const searchResults = await weaviateService.search(
        selectedCollection.name,
        queryText,
        method as "nearText" | "nearVector" | "bm25" | "hybrid",
        settings
      );
      setResults(searchResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
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
      <header className="bg-white shadow-sm border-b border-gray-200 flex-shrink-0">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">
                Weaviate Retrievals Playground
              </h1>
              {taskId && (
                <span className="ml-2 text-sm text-gray-500">
                  Task: {taskId}
                </span>
              )}
            </div>

            {isConnected && (
              <div className="flex items-center space-x-4">
                <div className="flex items-center text-sm text-gray-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  <span>Connected to Weaviate</span>
                  <span className="ml-2 text-gray-400">({connectionUrl})</span>
                </div>
                <button
                  onClick={handleDisconnect}
                  className="text-sm text-gray-600 hover:text-gray-900"
                >
                  Disconnect
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

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
                  ) : (
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
                  )}
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
};
