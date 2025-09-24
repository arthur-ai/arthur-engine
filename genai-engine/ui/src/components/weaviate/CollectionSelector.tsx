"use client";

import React, { useState, useEffect } from "react";
import { WeaviateCollection, weaviateService } from "@/lib/weaviate-client";

interface CollectionSelectorProps {
  onCollectionSelect: (collection: WeaviateCollection | null) => void;
  selectedCollection: WeaviateCollection | null;
}

export const CollectionSelector: React.FC<CollectionSelectorProps> = ({
  onCollectionSelect,
  selectedCollection,
}) => {
  const [collections, setCollections] = useState<WeaviateCollection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Record<string, any>>({});

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

  const handleCollectionClick = (collection: WeaviateCollection) => {
    if (selectedCollection?.name === collection.name) {
      onCollectionSelect(null);
    } else {
      onCollectionSelect(collection);
    }
  };

  const handleRefresh = () => {
    fetchCollections();
  };

  if (loading) {
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
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Collections</h3>
          <button
            onClick={handleRefresh}
            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh
          </button>
        </div>
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
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">
          Collections ({collections.length})
        </h3>
        <button
          onClick={handleRefresh}
          className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
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
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </button>
      </div>

      {collections.length === 0 ? (
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
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No collections found
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            No collections are available in your Weaviate instance.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {collections.map((collection) => {
            const isSelected = selectedCollection?.name === collection.name;
            const collectionStats = stats[collection.name] || {
              totalObjects: 0,
              vectorizer: "unknown",
              properties: 0,
            };

            return (
              <div
                key={collection.name}
                onClick={() => handleCollectionClick(collection)}
                className={`p-4 border rounded-lg cursor-pointer transition-all duration-200 ${
                  isSelected
                    ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <h4 className="text-sm font-medium text-gray-900">
                        {collection.name}
                      </h4>
                      {isSelected && (
                        <svg
                          className="ml-2 h-4 w-4 text-blue-500"
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
                      )}
                    </div>

                    {collection.description && (
                      <p className="mt-1 text-sm text-gray-600">
                        {collection.description}
                      </p>
                    )}

                    <div className="mt-2 flex flex-wrap gap-2">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {collectionStats.totalObjects} objects
                      </span>
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {collectionStats.properties} properties
                      </span>
                      {collectionStats.vectorizer &&
                        collectionStats.vectorizer !== "unknown" && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {collectionStats.vectorizer}
                          </span>
                        )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selectedCollection && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex items-center">
            <svg
              className="h-4 w-4 text-blue-500 mr-2"
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
            <span className="text-sm text-blue-800">
              Selected: <strong>{selectedCollection.name}</strong>
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
