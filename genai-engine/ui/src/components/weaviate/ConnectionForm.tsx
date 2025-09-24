"use client";

import React, { useState } from "react";
import { WeaviateConnection } from "@/lib/weaviate-client";

interface ConnectionFormProps {
  onConnect: (connection: WeaviateConnection) => Promise<boolean>;
  isConnecting: boolean;
  isConnected: boolean;
  onDisconnect: () => void;
}

export const ConnectionForm: React.FC<ConnectionFormProps> = ({
  onConnect,
  isConnecting,
  isConnected,
  onDisconnect,
}) => {
  const [url, setUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!url.trim() || !apiKey.trim()) {
      setError("Please provide both URL and API key");
      return;
    }

    // Basic URL validation
    try {
      new URL(url);
    } catch {
      setError("Please enter a valid URL");
      return;
    }

    const success = await onConnect({ url: url.trim(), apiKey: apiKey.trim() });
    if (!success) {
      setError("Failed to connect. Please check your URL and API key.");
    }
  };

  const handleDisconnect = () => {
    onDisconnect();
    setUrl("");
    setApiKey("");
    setError(null);
  };

  if (isConnected) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            Connected to Weaviate
          </h3>
          <button
            onClick={handleDisconnect}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-900 !text-gray-900 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
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
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
            Disconnect
          </button>
        </div>
        <div className="flex items-center text-sm text-gray-600">
          <svg
            className="h-4 w-4 mr-2 text-green-500"
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
          Connected to: {url}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4 !text-gray-900">
        Connect to Weaviate
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="url"
            className="block text-sm font-medium text-gray-900 mb-1 !text-gray-900"
          >
            Weaviate URL
          </label>
          <input
            type="url"
            id="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://your-weaviate-instance.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 !text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            disabled={isConnecting}
          />
          <p className="mt-1 text-xs text-gray-600">
            Enter the full URL to your Weaviate instance
          </p>
        </div>

        <div>
          <label
            htmlFor="apiKey"
            className="block text-sm font-medium text-gray-900 mb-1 !text-gray-900"
          >
            API Key
          </label>
          <input
            type="password"
            id="apiKey"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter your Weaviate API key"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 !text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            disabled={isConnecting}
          />
          <p className="mt-1 text-xs text-gray-600">
            Your Weaviate API key for authentication
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
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
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={isConnecting || !url.trim() || !apiKey.trim()}
          className="w-full flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isConnecting ? (
            <>
              <svg
                className="animate-spin -ml-1 mr-3 h-4 w-4 text-white"
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
              Connecting...
            </>
          ) : (
            "Connect"
          )}
        </button>
      </form>
    </div>
  );
};
