import { API_KIND_TO_SEARCH_METHOD, SEARCH_METHOD_TO_API_KIND, isHybridSettings, isVectorSettings } from "../types";
import type { ApiSearchKind, ApiSearchSettings, ApiSearchSettingsRequest, SearchMethod, SearchSettings } from "../types";

import { DEFAULT_SEARCH_SETTINGS } from "@/constants/search";
import type {
  WeaviateHybridSearchSettingsConfigurationRequest,
  WeaviateKeywordSearchSettingsConfigurationRequest,
  WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
} from "@/lib/api-client/api-client";

/**
 * Convert SearchMethod to ApiSearchKind
 */
export function getApiKindFromMethod(method: SearchMethod): ApiSearchKind {
  return SEARCH_METHOD_TO_API_KIND[method];
}

/**
 * Convert ApiSearchKind to SearchMethod
 */
export function getMethodFromApiKind(kind: string): SearchMethod {
  return API_KIND_TO_SEARCH_METHOD[kind as ApiSearchKind] ?? "nearText";
}

export function normalizeIncludeVector(value: boolean | string | string[] | null | undefined): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") return true;
  if (Array.isArray(value)) return value.length > 0;
  return false;
}

/**
 * Convert API search settings to local SearchSettings format.
 */
export function mapApiSettingsToLocal(settings: ApiSearchSettings): SearchSettings {
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

/**
 * Default return metadata fields for search requests
 */
const DEFAULT_RETURN_METADATA = ["distance", "certainty", "score", "explain_score"] as const;

/**
 * Build API search settings from local SearchSettings and SearchMethod.
 */
export function buildApiSearchSettings(collectionName: string, method: SearchMethod, settings: SearchSettings): ApiSearchSettingsRequest {
  const base = {
    collection_name: collectionName,
    limit: settings.limit,
    include_vector: settings.includeVector,
    return_properties: settings.includeMetadata ? undefined : [],
    return_metadata: [...DEFAULT_RETURN_METADATA],
  };

  switch (method) {
    case "nearText":
      return {
        ...base,
        certainty: 1 - settings.distance,
      } as WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest;

    case "bm25":
      return base as WeaviateKeywordSearchSettingsConfigurationRequest;

    case "hybrid":
      return {
        ...base,
        alpha: settings.alpha,
        certainty: 1 - settings.distance,
      } as WeaviateHybridSearchSettingsConfigurationRequest;
  }
}

/**
 * Build API search settings with search_kind included (for unsaved configs in experiments).
 */
export function buildApiSearchSettingsWithKind(
  collectionName: string,
  method: SearchMethod,
  settings: SearchSettings
): ApiSearchSettingsRequest & { search_kind: ApiSearchKind } {
  const baseSettings = buildApiSearchSettings(collectionName, method, settings);
  return {
    ...baseSettings,
    search_kind: SEARCH_METHOD_TO_API_KIND[method],
  };
}
