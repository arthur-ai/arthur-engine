export interface SearchSettings {
  limit: number;
  distance: number;
  alpha: number;
  includeVector: boolean;
  includeMetadata: boolean;
}

export type SearchMethod = "nearText" | "bm25" | "hybrid";

export const SEARCH_METHOD_TO_API_KIND = {
  nearText: "vector_similarity_text_search",
  bm25: "keyword_search",
  hybrid: "hybrid_search",
} as const satisfies Record<SearchMethod, string>;
