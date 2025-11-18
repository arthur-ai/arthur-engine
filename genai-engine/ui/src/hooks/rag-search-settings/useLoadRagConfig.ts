import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import type {
  RagProviderCollectionResponse,
  RagSearchSettingConfigurationResponse,
  WeaviateHybridSearchSettingsConfigurationResponse,
  WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse,
  WeaviateKeywordSearchSettingsConfigurationResponse,
} from "@/lib/api-client/api-client";

type ApiSearchSettings =
  | WeaviateHybridSearchSettingsConfigurationResponse
  | WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse
  | WeaviateKeywordSearchSettingsConfigurationResponse;

export interface LoadedConfigData {
  config: RagSearchSettingConfigurationResponse;
  versionNumber: number;
  searchKind: "hybrid_search" | "vector_similarity_text_search" | "keyword_search";
  collection: RagProviderCollectionResponse | null;
  settings: ApiSearchSettings;
}

export function useLoadRagConfig(configId: string | null, versionNumber?: number) {
  const api = useApi();

  return useQuery({
    queryKey: ["loadRagConfig", configId, versionNumber, api],
    queryFn: async (): Promise<LoadedConfigData> => {
      if (!api || !configId) {
        throw new Error("API client or config ID not available");
      }

      const configResponse = await api.api.getRagSearchSetting(configId);
      const config = configResponse.data;

      const versionToLoad = versionNumber ?? config.latest_version_number;
      const versionResponse = await api.api.getRagSearchSettingVersion(configId, versionToLoad);
      const version = versionResponse.data;

      const { settings: apiSettings } = version;
      if (!apiSettings) {
        throw new Error("Version settings not available");
      }

      let foundCollection: RagProviderCollectionResponse | null = null;

      if (config.rag_provider_id) {
        try {
          const collectionsResponse = await api.api.listRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGet(config.rag_provider_id);
          const providerCollections = collectionsResponse.data.rag_provider_collections;
          foundCollection = providerCollections.find((c: RagProviderCollectionResponse) => c.identifier === apiSettings.collection_name) || null;
        } catch (err) {
          console.error("[RAG] Failed to fetch collections for config:", err);
        }
      }

      return {
        config,
        versionNumber: versionToLoad,
        searchKind: apiSettings.search_kind!,
        collection: foundCollection,
        settings: apiSettings,
      };
    },
    enabled: !!configId && !!api,
  });
}
