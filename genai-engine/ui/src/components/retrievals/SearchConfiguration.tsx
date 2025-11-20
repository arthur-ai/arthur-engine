import React, { useState } from "react";

import { CollectionSelector } from "./CollectionSelector";
import { ProviderSelector } from "./ProviderSelector";
import { QueryInput } from "./QueryInput";
import { SearchActions } from "./SearchActions";
import { SearchMethodSelector } from "./SearchMethodSelector";
import { SearchSettings } from "./SearchSettings";
import type { SearchSettings as SearchSettingsType, SearchMethod } from "./types";

import type { RagProviderConfigurationResponse, RagProviderCollectionResponse } from "@/lib/api-client/api-client";
import { downloadJson } from "@/utils/fileDownload";

interface SearchConfigurationProps {
  selectedProviderId: string;
  onProviderChange: (providerId: string) => void;
  providers: RagProviderConfigurationResponse[];
  isLoadingProviders: boolean;
  onManageProviders: () => void;
  selectedCollection: RagProviderCollectionResponse | null;
  onCollectionSelect: (collection: RagProviderCollectionResponse | null) => void;
  onExecuteQuery: (query: string, searchMethod: SearchMethod) => void;
  isExecuting: boolean;
  searchMethod: SearchMethod;
  onSearchMethodChange: (method: SearchMethod) => void;
  settings: SearchSettingsType;
  onSettingsChange: (settings: SearchSettingsType) => void;
  collections: RagProviderCollectionResponse[];
  onRefresh: () => void;
}

export const SearchConfiguration: React.FC<SearchConfigurationProps> = ({
  selectedProviderId,
  onProviderChange,
  providers,
  isLoadingProviders,
  onManageProviders,
  selectedCollection,
  onCollectionSelect,
  onExecuteQuery,
  isExecuting,
  searchMethod,
  onSearchMethodChange,
  settings,
  onSettingsChange,
  collections,
  onRefresh,
}) => {
  const [query, setQuery] = useState("");

  const effectiveCollection = selectedCollection || (collections.length > 0 ? collections[0] : null);

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    if (query.trim() && effectiveCollection) {
      if (!selectedCollection && effectiveCollection) {
        onCollectionSelect(effectiveCollection);
      }
      onExecuteQuery(query.trim(), searchMethod);
    }
  };

  const handleClear = (): void => {
    setQuery("");
  };

  const handleExportConfig = (): void => {
    const relevantSettings: {
      limit: number;
      includeMetadata: boolean;
      includeVector: boolean;
      distance?: number;
      alpha?: number;
    } = {
      limit: settings.limit,
      includeMetadata: settings.includeMetadata,
      includeVector: settings.includeVector,
    };

    if (searchMethod === "nearText" || searchMethod === "hybrid") {
      relevantSettings.distance = settings.distance;
    }

    if (searchMethod === "hybrid") {
      relevantSettings.alpha = settings.alpha;
    }

    const exportData = {
      collection: effectiveCollection?.identifier || null,
      searchMethod,
      query,
      settings: relevantSettings,
      timestamp: new Date().toISOString(),
    };

    downloadJson(exportData, "rag-search-config");
  };

  const isDisabled = !effectiveCollection || !query.trim() || isExecuting;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="space-y-4">
        <ProviderSelector
          selectedProviderId={selectedProviderId}
          onProviderChange={onProviderChange}
          providers={providers}
          isLoadingProviders={isLoadingProviders}
          onManageProviders={onManageProviders}
          isExecuting={isExecuting}
        />

        {selectedProviderId && (
          <>
            <CollectionSelector
              onCollectionSelect={onCollectionSelect}
              collections={collections}
              onRefresh={onRefresh}
              isExecuting={isExecuting}
              effectiveCollection={effectiveCollection}
            />

            <SearchMethodSelector searchMethod={searchMethod} onSearchMethodChange={onSearchMethodChange} isExecuting={isExecuting} />

            <QueryInput query={query} onQueryChange={setQuery} onClear={handleClear} isExecuting={isExecuting} />

            <SearchSettings searchMethod={searchMethod} settings={settings} onSettingsChange={onSettingsChange} isExecuting={isExecuting} />

            <SearchActions
              onExportConfig={handleExportConfig}
              onClear={handleClear}
              onSubmit={handleSubmit}
              isDisabled={isDisabled}
              isExecuting={isExecuting}
              hasQuery={!!query}
            />
          </>
        )}
      </div>
    </div>
  );
};
