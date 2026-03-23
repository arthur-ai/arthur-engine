import type {
  WeaviateHybridSearchSettingsConfigurationRequest,
  WeaviateHybridSearchSettingsConfigurationResponse,
  WeaviateKeywordSearchSettingsConfigurationRequest,
  WeaviateKeywordSearchSettingsConfigurationResponse,
  WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
  WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse,
} from "@/lib/api-client/api-client";

export interface SearchSettings {
  limit: number;
  distance: number;
  alpha: number;
  includeVector: boolean;
  includeMetadata: boolean;
}

export type SearchMethod = "nearText" | "bm25" | "hybrid";

export type ApiSearchKind = "vector_similarity_text_search" | "keyword_search" | "hybrid_search";

export const SEARCH_METHOD_TO_API_KIND: Record<SearchMethod, ApiSearchKind> = {
  nearText: "vector_similarity_text_search",
  bm25: "keyword_search",
  hybrid: "hybrid_search",
} as const;

export const API_KIND_TO_SEARCH_METHOD: Record<ApiSearchKind, SearchMethod> = {
  vector_similarity_text_search: "nearText",
  keyword_search: "bm25",
  hybrid_search: "hybrid",
} as const;

/**
 * Union type for all API search settings response types
 */
export type ApiSearchSettings =
  | WeaviateHybridSearchSettingsConfigurationResponse
  | WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse
  | WeaviateKeywordSearchSettingsConfigurationResponse;

/**
 * Union type for all API search settings request types
 */
export type ApiSearchSettingsRequest =
  | WeaviateHybridSearchSettingsConfigurationRequest
  | WeaviateKeywordSearchSettingsConfigurationRequest
  | WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest;

/**
 * Type guard to check if settings are hybrid search settings
 */
export function isHybridSettings(settings: ApiSearchSettings): settings is WeaviateHybridSearchSettingsConfigurationResponse {
  return settings !== null && settings.search_kind === "hybrid_search";
}

/**
 * Type guard to check if settings are vector similarity search settings
 */
export function isVectorSettings(settings: ApiSearchSettings): settings is WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse {
  return settings !== null && settings.search_kind === "vector_similarity_text_search";
}
