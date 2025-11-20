import React, { useState } from "react";

import type { SearchSettings, SearchMethod } from "./types";

import { RagProvidersModal } from "@/components/rag/RagProvidersModal";
import { ResultsDisplay } from "@/components/retrievals/ResultsDisplay";
import { SearchConfiguration } from "@/components/retrievals/SearchConfiguration";
import { getContentHeight } from "@/constants/layout";
import { DEFAULT_SEARCH_SETTINGS } from "@/constants/search";
import { useRagCollections } from "@/hooks/rag/useRagCollections";
import { useRagProviders } from "@/hooks/rag/useRagProviders";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { WeaviateQueryResults, RagProviderCollectionResponse } from "@/lib/api-client/api-client";

export const RagRetrievalsPlayground: React.FC = () => {
  const api = useApi();
  const { task } = useTask();

  const [selectedProviderId, setSelectedProviderId] = useState<string>("");
  const [selectedCollection, setSelectedCollection] = useState<RagProviderCollectionResponse | null>(null);
  const [query, setQuery] = useState("");
  const [searchMethod, setSearchMethod] = useState<SearchMethod>("nearText");
  const [settings, setSettings] = useState<SearchSettings>(DEFAULT_SEARCH_SETTINGS);
  const [results, setResults] = useState<WeaviateQueryResults | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { providers, isLoading: isLoadingProviders, refetch: refetchProviders } = useRagProviders(task?.id);

  const effectiveProviderId = selectedProviderId || (providers.length > 0 ? providers[0].id : "");
  const { collections, refetch: refetchCollections } = useRagCollections(effectiveProviderId);

  const handleProviderChange = (providerId: string) => {
    setSelectedProviderId(providerId);
    setSelectedCollection(null);
    setResults(null);
    setError(null);
  };

  const handleCollectionSelect = (collection: RagProviderCollectionResponse | null) => {
    setSelectedCollection(collection);
    setResults(null);
    setError(null);
  };

  const handleExecuteQuery = async (queryText: string, method: SearchMethod) => {
    if (!selectedCollection || !selectedProviderId || !api) return;

    setIsExecuting(true);
    setError(null);
    setQuery(queryText);

    try {
      let response;

      if (method === "nearText") {
        response = await api.api.executeSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPost(selectedProviderId, {
          settings: {
            collection_name: selectedCollection.identifier,
            query: queryText,
            limit: settings.limit,
            certainty: 1 - settings.distance,
            return_properties: settings.includeMetadata ? undefined : [],
            include_vector: settings.includeVector,
            return_metadata: ["distance", "certainty", "score", "explain_score"],
          },
        });
      } else if (method === "bm25") {
        response = await api.api.executeKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPost(selectedProviderId, {
          settings: {
            collection_name: selectedCollection.identifier,
            query: queryText,
            limit: settings.limit,
            return_properties: settings.includeMetadata ? undefined : [],
            include_vector: settings.includeVector,
            return_metadata: ["distance", "certainty", "score", "explain_score"],
          },
        });
      } else if (method === "hybrid") {
        response = await api.api.executeHybridSearchApiV1RagProvidersProviderIdHybridSearchPost(selectedProviderId, {
          settings: {
            collection_name: selectedCollection.identifier,
            query: queryText,
            limit: settings.limit,
            alpha: settings.alpha,
            return_properties: settings.includeMetadata ? undefined : [],
            include_vector: settings.includeVector,
            return_metadata: ["distance", "certainty", "score", "explain_score"],
          },
        });
      }

      if (response) {
        setResults(response.data.response);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setIsExecuting(false);
    }
  };

  const handleSettingsChange = (newSettings: SearchSettings) => {
    setSettings(newSettings);
  };

  const handleManageProviders = () => {
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    refetchProviders();
  };

  return (
    <div className="bg-gray-50 flex flex-col" style={{ height: getContentHeight() }}>
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 px-4 sm:px-6 lg:px-8 py-6 overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-[600px_1fr] gap-6 h-full overflow-hidden">
            <div className="flex flex-col h-full overflow-hidden">
              <div className="flex-1 overflow-y-auto pb-6">
                <SearchConfiguration
                  selectedProviderId={effectiveProviderId}
                  onProviderChange={handleProviderChange}
                  providers={providers}
                  isLoadingProviders={isLoadingProviders}
                  onManageProviders={handleManageProviders}
                  selectedCollection={selectedCollection}
                  onCollectionSelect={handleCollectionSelect}
                  onExecuteQuery={handleExecuteQuery}
                  isExecuting={isExecuting}
                  searchMethod={searchMethod}
                  onSearchMethodChange={setSearchMethod}
                  settings={settings}
                  onSettingsChange={handleSettingsChange}
                  collections={collections}
                  onRefresh={refetchCollections}
                />
              </div>
            </div>

            <div className="flex flex-col h-full overflow-hidden">
              <div className="flex-1 overflow-y-auto pb-6">
                <ResultsDisplay results={results} isLoading={isExecuting} error={error} query={query} searchMethod={searchMethod} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {task && <RagProvidersModal open={modalOpen} onClose={handleCloseModal} taskId={task.id} />}
    </div>
  );
};
