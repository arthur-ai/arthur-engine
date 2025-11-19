import React from "react";

import type { RagProviderCollectionResponse } from "@/lib/api-client/api-client";

interface CollectionSelectorProps {
  onCollectionSelect: (collection: RagProviderCollectionResponse | null) => void;
  collections: RagProviderCollectionResponse[];
  onRefresh: () => void;
  isExecuting: boolean;
  effectiveCollection: RagProviderCollectionResponse | null;
}

export const CollectionSelector: React.FC<CollectionSelectorProps> = ({
  onCollectionSelect,
  collections,
  onRefresh,
  isExecuting,
  effectiveCollection,
}) => {
  return (
    <div>
      <label htmlFor="collection" className="block text-sm font-medium text-gray-900 mb-2">
        Collection
      </label>
      <div className="flex items-center space-x-2">
        <select
          id="collection"
          value={effectiveCollection?.identifier || ""}
          onChange={(e) => {
            const collection = collections.find((c) => c.identifier === e.target.value);
            onCollectionSelect(collection || null);
          }}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          disabled={isExecuting}
          aria-label="Select RAG collection"
          aria-describedby="collection-description"
        >
          <option value="">Select a collection</option>
          {collections.map((collection) => (
            <option key={collection.identifier} value={collection.identifier}>
              {collection.identifier}
            </option>
          ))}
        </select>
        <button
          onClick={onRefresh}
          disabled={isExecuting}
          className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-900 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          aria-label="Refresh collections list"
          title="Refresh collections"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};
