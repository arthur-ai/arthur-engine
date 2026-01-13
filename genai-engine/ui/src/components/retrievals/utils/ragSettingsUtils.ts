import type { SearchSettings, ApiSearchSettings } from "../types";
import { isHybridSettings, isVectorSettings } from "../types";

import { DEFAULT_SEARCH_SETTINGS } from "@/constants/search";

export function normalizeIncludeVector(value: boolean | string | string[] | null | undefined): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") return true;
  if (Array.isArray(value)) return value.length > 0;
  return false;
}

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
