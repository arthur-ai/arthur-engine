import { parseAsInteger, parseAsString, useQueryStates } from "nuqs";
import React, { useState, useEffect } from "react";

import type { SearchSettings, SearchMethod } from "./types";

import { RagProvidersModal } from "@/components/rag/RagProvidersModal";
import { ResultsDisplay } from "@/components/retrievals/ResultsDisplay";
import { SearchConfiguration } from "@/components/retrievals/SearchConfiguration";
import { getContentHeight } from "@/constants/layout";
import { DEFAULT_SEARCH_SETTINGS } from "@/constants/search";
import { useRagCollections } from "@/hooks/rag/useRagCollections";
import { useRagProviders } from "@/hooks/rag/useRagProviders";
import { useLoadRagConfig } from "@/hooks/rag-search-settings/useLoadRagConfig";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type {
  WeaviateQueryResults,
  RagProviderCollectionResponse,
  RagSearchSettingConfigurationResponse,
  WeaviateHybridSearchSettingsConfigurationResponse,
  WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse,
  WeaviateKeywordSearchSettingsConfigurationResponse,
} from "@/lib/api-client/api-client";

interface SearchConfig {
  providerId: string;
  collection: RagProviderCollectionResponse | null;
  method: SearchMethod;
  settings: SearchSettings;
  query: string;
}

interface LoadedConfigSelection {
  configId: string;
  versionNumber?: number;
}

interface LoadedConfig {
  id: string;
  name: string;
  version: number;
}

interface ResultsState {
  data: WeaviateQueryResults | null;
  isLoading: boolean;
  error: string | null;
}

type ApiSearchSettings =
  | WeaviateHybridSearchSettingsConfigurationResponse
  | WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse
  | WeaviateKeywordSearchSettingsConfigurationResponse;

function isHybridSettings(settings: ApiSearchSettings): settings is WeaviateHybridSearchSettingsConfigurationResponse {
  return settings !== null && settings.search_kind === "hybrid_search";
}

function isVectorSettings(settings: ApiSearchSettings): settings is WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse {
  return settings !== null && settings.search_kind === "vector_similarity_text_search";
}

function normalizeIncludeVector(value: boolean | string | string[] | null | undefined): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") return true;
  if (Array.isArray(value)) return value.length > 0;
  return false;
}

function mapApiSettingsToLocal(settings: ApiSearchSettings): SearchSettings {
  const baseSettings: SearchSettings = {
    limit: settings.limit ?? DEFAULT_SEARCH_SETTINGS.limit,
    distance: DEFAULT_SEARCH_SETTINGS.distance,
    alpha: DEFAULT_SEARCH_SETTINGS.alpha,
    includeVector: normalizeIncludeVector(settings.include_vector),
    includeMetadata: !settings.return_properties || settings.return_properties.length > 0,
  };

  if (isHybridSettings(settings)) {
    // Hybrid: extract alpha and max_vector_distance (if present)
    baseSettings.alpha = settings.alpha ?? DEFAULT_SEARCH_SETTINGS.alpha;
    baseSettings.distance = settings.max_vector_distance ?? DEFAULT_SEARCH_SETTINGS.distance;
  } else if (isVectorSettings(settings)) {
    // Vector: prefer certainty converted to distance, fallback to distance
    if (settings.certainty !== null && settings.certainty !== undefined) {
      baseSettings.distance = 1 - settings.certainty;
    } else if (settings.distance !== null && settings.distance !== undefined) {
      baseSettings.distance = settings.distance;
    }
  }
  // Keyword: no distance/alpha needed, use defaults

  return baseSettings;
}

export const RagRetrievalsPlayground: React.FC = () => {
  const api = useApi();
  const { task } = useTask();
  const [urlParams, setUrlParams] = useQueryStates({
    configId: parseAsString,
    version: parseAsInteger,
  });

  const [modalOpen, setModalOpen] = useState(false);

  const [searchConfig, setSearchConfig] = useState<SearchConfig>({
    providerId: "",
    collection: null,
    method: "nearText",
    settings: DEFAULT_SEARCH_SETTINGS,
    query: "",
  });

  const [configSelection, setConfigSelection] = useState<LoadedConfigSelection | null>(null);

  const { data: loadedConfigData, isLoading: isLoadingConfig } = useLoadRagConfig(configSelection?.configId ?? null, configSelection?.versionNumber);

  const loadedConfig: LoadedConfig | null = loadedConfigData
    ? {
        id: loadedConfigData.config.id,
        name: loadedConfigData.config.name,
        version: loadedConfigData.versionNumber,
      }
    : null;

  const [resultsState, setResultsState] = useState<ResultsState>({
    data: null,
    isLoading: false,
    error: null,
  });

  const { providers, isLoading: isLoadingProviders, refetch: refetchProviders } = useRagProviders(task?.id);

  const effectiveProviderId = searchConfig.providerId || (providers.length > 0 ? providers[0].id : "");
  const { collections, refetch: refetchCollections } = useRagCollections(effectiveProviderId);

  useEffect(() => {
    if (loadedConfigData) {
      const { config, settings, collection, searchKind } = loadedConfigData;

      let method: SearchMethod;
      if (searchKind === "hybrid_search") {
        method = "hybrid";
      } else if (searchKind === "vector_similarity_text_search") {
        method = "nearText";
      } else {
        method = "bm25";
      }

      setSearchConfig({
        providerId: config.rag_provider_id || "",
        collection,
        method,
        settings: mapApiSettingsToLocal(settings),
        query: "",
      });
    }
  }, [loadedConfigData]);

  const handleProviderChange = (providerId: string) => {
    setSearchConfig((prev) => ({
      ...prev,
      providerId,
      collection: null,
    }));
    setResultsState({
      data: null,
      isLoading: false,
      error: null,
    });
  };

  const handleCollectionSelect = (collection: RagProviderCollectionResponse | null) => {
    setSearchConfig((prev) => ({
      ...prev,
      collection,
    }));
    setResultsState({
      data: null,
      isLoading: false,
      error: null,
    });
  };

  const handleExecuteQuery = async (queryText: string, method: SearchMethod) => {
    if (!searchConfig.collection || !searchConfig.providerId || !api) return;

    setResultsState({
      data: null,
      isLoading: true,
      error: null,
    });
    setSearchConfig((prev) => ({ ...prev, query: queryText }));

    try {
      let response;

      if (method === "nearText") {
        response = await api.api.executeSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPost(searchConfig.providerId, {
          settings: {
            collection_name: searchConfig.collection.identifier,
            query: queryText,
            limit: searchConfig.settings.limit,
            certainty: 1 - searchConfig.settings.distance,
            return_properties: searchConfig.settings.includeMetadata ? undefined : [],
            include_vector: searchConfig.settings.includeVector,
            return_metadata: ["distance", "certainty", "score", "explain_score"],
          },
        });
      } else if (method === "bm25") {
        response = await api.api.executeKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPost(searchConfig.providerId, {
          settings: {
            collection_name: searchConfig.collection.identifier,
            query: queryText,
            limit: searchConfig.settings.limit,
            return_properties: searchConfig.settings.includeMetadata ? undefined : [],
            include_vector: searchConfig.settings.includeVector,
            return_metadata: ["distance", "certainty", "score", "explain_score"],
          },
        });
      } else if (method === "hybrid") {
        response = await api.api.executeHybridSearchApiV1RagProvidersProviderIdHybridSearchPost(searchConfig.providerId, {
          settings: {
            collection_name: searchConfig.collection.identifier,
            query: queryText,
            limit: searchConfig.settings.limit,
            alpha: searchConfig.settings.alpha,
            return_properties: searchConfig.settings.includeMetadata ? undefined : [],
            include_vector: searchConfig.settings.includeVector,
            return_metadata: ["distance", "certainty", "score", "explain_score"],
          },
        });
      }

      if (response) {
        setResultsState({
          data: response.data.response,
          isLoading: false,
          error: null,
        });
      }
    } catch (err) {
      setResultsState({
        data: null,
        isLoading: false,
        error: err instanceof Error ? err.message : "Search failed",
      });
    }
  };

  const handleSettingsChange = (newSettings: SearchSettings) => {
    setSearchConfig((prev) => ({ ...prev, settings: newSettings }));
  };

  const handleManageProviders = () => {
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    refetchProviders();
  };

  const handleVersionSelect = (versionNumber: number) => {
    if (loadedConfig) {
      setConfigSelection({ configId: loadedConfig.id, versionNumber });
    }
  };

  const handleConfigSelectFromSelector = (config: RagSearchSettingConfigurationResponse | null) => {
    if (config) {
      setConfigSelection({ configId: config.id });
    } else {
      // Clear selection
      setConfigSelection(null);
    }
  };

  // URL param handling - load config from URL if present
  useEffect(() => {
    if (urlParams.configId && !configSelection) {
      setConfigSelection({
        configId: urlParams.configId,
        versionNumber: urlParams.version ?? undefined,
      });
      // Clear params after setting selection
      setUrlParams({ configId: null, version: null });
    }
  }, [urlParams.configId, urlParams.version, configSelection, setUrlParams]);

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
                  selectedCollection={searchConfig.collection}
                  onCollectionSelect={handleCollectionSelect}
                  onExecuteQuery={handleExecuteQuery}
                  isExecuting={resultsState.isLoading}
                  searchMethod={searchConfig.method}
                  onSearchMethodChange={(method) => setSearchConfig((prev) => ({ ...prev, method }))}
                  settings={searchConfig.settings}
                  onSettingsChange={handleSettingsChange}
                  collections={collections}
                  onRefresh={refetchCollections}
                  currentConfigId={loadedConfig?.id ?? null}
                  currentConfigName={loadedConfig?.name ?? null}
                  currentVersion={loadedConfig?.version ?? null}
                  onConfigSelect={handleConfigSelectFromSelector}
                  onVersionSelect={handleVersionSelect}
                  taskId={task?.id || ""}
                  isLoadingConfig={isLoadingConfig}
                />
              </div>
            </div>

            <div className="flex flex-col h-full overflow-hidden">
              <div className="flex-1 overflow-y-auto pb-6">
                <ResultsDisplay
                  results={resultsState.data}
                  isLoading={resultsState.isLoading}
                  error={resultsState.error}
                  query={searchConfig.query}
                  searchMethod={searchConfig.method}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {task && <RagProvidersModal open={modalOpen} onClose={handleCloseModal} taskId={task.id} />}
    </div>
  );
};
