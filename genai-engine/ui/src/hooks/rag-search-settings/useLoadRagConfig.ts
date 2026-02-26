import { useMutation, useQuery } from "@tanstack/react-query";

import type { ApiSearchSettings } from "@/components/retrievals/types";
import { useApi } from "@/hooks/useApi";
import type { RagProviderCollectionResponse, RagSearchSettingConfigurationResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

export interface LoadedConfigData {
  config: RagSearchSettingConfigurationResponse;
  versionNumber: number;
  searchKind: "hybrid_search" | "vector_similarity_text_search" | "keyword_search";
  collection: RagProviderCollectionResponse | null;
  settings: ApiSearchSettings;
  tags: string[];
}

interface LoadConfigParams {
  configId: string;
  versionNumber?: number;
}

async function fetchConfigData(api: ReturnType<typeof useApi>, configId: string, versionNumber?: number): Promise<LoadedConfigData> {
  if (!api) {
    throw new Error("API client not available");
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
    } catch {
      // Collections fetch failed - foundCollection remains null
    }
  }

  return {
    config,
    versionNumber: versionToLoad,
    searchKind: apiSettings.search_kind!,
    collection: foundCollection,
    settings: apiSettings,
    tags: version.tags ?? [],
  };
}

export function useLoadRagConfig(configId: string | null, versionNumber?: number) {
  const api = useApi();

  return useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps -- api is a stable hook reference, not a serializable cache key
    queryKey: queryKeys.ragSearchSettings.load(configId!, versionNumber),
    queryFn: () => fetchConfigData(api, configId!, versionNumber),
    enabled: !!configId && !!api,
  });
}

export function useLoadRagConfigMutation() {
  const api = useApi();

  return useMutation({
    mutationFn: ({ configId, versionNumber }: LoadConfigParams) => fetchConfigData(api, configId, versionNumber),
  });
}
