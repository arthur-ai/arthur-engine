import { v4 as uuidv4 } from "uuid";

import type { RagPanel, RagPanelsState } from "../ragPanelsReducer";
import { createPanel } from "../ragPanelsReducer";
import type { SearchSettings } from "../types";

import { buildApiSearchSettingsWithKind, getMethodFromApiKind } from "./ragSettingsUtils";

import { DEFAULT_SEARCH_SETTINGS } from "@/constants/search";
import type {
  RagNotebookState,
  RagNotebookStateResponse,
  SavedRagConfigInput,
  SavedRagConfigOutput,
  UnsavedRagConfig,
  UnsavedRagConfigResponse,
  DatasetRefInput,
  EvalRefInput,
  RagProviderCollectionResponse,
  Api,
} from "@/lib/api-client/api-client";

export interface RagExperimentConfig {
  name: string;
  description: string;
  dataset_ref: DatasetRefInput | null;
  eval_list: EvalRefInput[];
  query_column?: string;
  /** Per-panel query column mappings: panelId -> column name */
  query_column_mappings?: { [panelId: string]: string };
  dataset_row_filter?: { column_name: string; column_value: string }[];
  /** Eval variable mappings for each evaluator */
  eval_variable_mappings?: {
    evalName: string;
    evalVersion: number;
    mappings: {
      [variableName: string]: {
        sourceType: "dataset_column" | "experiment_output";
        datasetColumn?: string;
        jsonPath?: string;
      };
    };
  }[];
}

function panelToRagConfig(
  panel: RagPanel,
  queryColumn: string = "query"
): ({ type: "saved" } & SavedRagConfigInput) | ({ type: "unsaved" } & UnsavedRagConfig) | null {
  if (panel.providerId && panel.collection) {
    const settings = buildApiSearchSettingsWithKind(panel.collection.identifier, panel.method, panel.settings);

    return {
      type: "unsaved",
      unsaved_id: panel.id,
      rag_provider_id: panel.providerId,
      settings,
      query_column: {
        type: "dataset_column",
        dataset_column: { name: queryColumn },
      },
    };
  }

  if (panel.loadedConfigId && panel.loadedVersion !== null) {
    return {
      type: "saved",
      setting_configuration_id: panel.loadedConfigId,
      version: panel.loadedVersion,
      query_column: {
        type: "dataset_column",
        dataset_column: { name: queryColumn },
      },
    };
  }

  return null;
}

export function serializeRagPanelsState(state: RagPanelsState, experimentConfig?: RagExperimentConfig): RagNotebookState {
  const defaultQueryColumn = experimentConfig?.query_column || "query";
  const queryColumnMappings = experimentConfig?.query_column_mappings || {};

  const ragConfigs = state.panels
    .map((panel) => {
      const queryColumn = queryColumnMappings[panel.id] || defaultQueryColumn;
      return panelToRagConfig(panel, queryColumn);
    })
    .filter((config): config is NonNullable<ReturnType<typeof panelToRagConfig>> => config !== null);

  if (experimentConfig && experimentConfig.dataset_ref) {
    return {
      rag_configs: ragConfigs.length > 0 ? ragConfigs : null,
      dataset_ref: experimentConfig.dataset_ref,
      eval_list: experimentConfig.eval_list.length > 0 ? experimentConfig.eval_list : null,
      dataset_row_filter:
        experimentConfig.dataset_row_filter?.map((f) => ({
          column_name: f.column_name,
          column_value: f.column_value,
        })) || null,
    };
  }

  return {
    rag_configs: ragConfigs.length > 0 ? ragConfigs : null,
    dataset_ref: null,
    eval_list: null,
    dataset_row_filter: null,
  };
}

async function savedConfigToPanel(config: SavedRagConfigOutput, apiClient: Api<unknown>): Promise<RagPanel | null> {
  try {
    const response = await apiClient.api.getRagSearchSetting(config.setting_configuration_id);
    const configData = response.data;

    const versionResponse = await apiClient.api.getRagSearchSettingVersion(config.setting_configuration_id, config.version);
    const versionData = versionResponse.data;
    const settings = versionData.settings;

    const searchKind = settings?.search_kind || "vector_similarity_text_search";
    const method = getMethodFromApiKind(searchKind);

    const panelSettings: SearchSettings = {
      limit: settings?.limit ?? DEFAULT_SEARCH_SETTINGS.limit,
      distance: DEFAULT_SEARCH_SETTINGS.distance,
      alpha: DEFAULT_SEARCH_SETTINGS.alpha,
      includeVector: typeof settings?.include_vector === "boolean" ? settings.include_vector : false,
      includeMetadata: !settings?.return_properties || settings.return_properties.length > 0,
    };

    if (searchKind === "hybrid_search" && settings) {
      const hybridSettings = settings as { alpha?: number; max_vector_distance?: number };
      panelSettings.alpha = hybridSettings.alpha ?? DEFAULT_SEARCH_SETTINGS.alpha;
      panelSettings.distance = hybridSettings.max_vector_distance ?? DEFAULT_SEARCH_SETTINGS.distance;
    } else if (searchKind === "vector_similarity_text_search" && settings) {
      const vectorSettings = settings as { certainty?: number; distance?: number };
      if (vectorSettings.certainty !== null && vectorSettings.certainty !== undefined) {
        panelSettings.distance = 1 - vectorSettings.certainty;
      } else if (vectorSettings.distance !== null && vectorSettings.distance !== undefined) {
        panelSettings.distance = vectorSettings.distance;
      }
    }

    const collection: RagProviderCollectionResponse | null = settings?.collection_name ? { identifier: settings.collection_name } : null;

    return {
      id: uuidv4(),
      providerId: configData.rag_provider_id || "",
      collection,
      method,
      settings: panelSettings,
      loadedConfigId: config.setting_configuration_id,
      loadedConfigName: configData.name,
      loadedVersion: config.version,
      results: null,
      isLoading: false,
      error: null,
    };
  } catch (error) {
    console.error(`Failed to fetch saved RAG config ${config.setting_configuration_id}:`, error);
    return null;
  }
}

function unsavedConfigToPanel(config: UnsavedRagConfigResponse): RagPanel {
  const settings = config.settings;
  const searchKind = settings?.search_kind || "vector_similarity_text_search";
  const method = getMethodFromApiKind(searchKind);

  const panelSettings: SearchSettings = {
    limit: settings?.limit ?? DEFAULT_SEARCH_SETTINGS.limit,
    distance: DEFAULT_SEARCH_SETTINGS.distance,
    alpha: DEFAULT_SEARCH_SETTINGS.alpha,
    includeVector: typeof settings?.include_vector === "boolean" ? settings.include_vector : false,
    includeMetadata: !settings?.return_properties || settings.return_properties.length > 0,
  };

  if (searchKind === "hybrid_search" && settings) {
    const hybridSettings = settings as { alpha?: number; max_vector_distance?: number };
    panelSettings.alpha = hybridSettings.alpha ?? DEFAULT_SEARCH_SETTINGS.alpha;
    panelSettings.distance = hybridSettings.max_vector_distance ?? DEFAULT_SEARCH_SETTINGS.distance;
  } else if (searchKind === "vector_similarity_text_search" && settings) {
    const vectorSettings = settings as { certainty?: number; distance?: number };
    if (vectorSettings.certainty !== null && vectorSettings.certainty !== undefined) {
      panelSettings.distance = 1 - vectorSettings.certainty;
    } else if (vectorSettings.distance !== null && vectorSettings.distance !== undefined) {
      panelSettings.distance = vectorSettings.distance;
    }
  }

  const collection: RagProviderCollectionResponse | null = settings?.collection_name ? { identifier: settings.collection_name } : null;

  return {
    id: config.unsaved_id || uuidv4(),
    providerId: config.rag_provider_id || "",
    collection,
    method,
    settings: panelSettings,
    loadedConfigId: null,
    loadedConfigName: null,
    loadedVersion: null,
    results: null,
    isLoading: false,
    error: null,
  };
}

export async function deserializeRagNotebookState(
  notebookState: RagNotebookStateResponse,
  apiClient: Api<unknown>
): Promise<{
  panels: RagPanel[];
  experimentConfig: RagExperimentConfig | null;
  fullState: RagNotebookStateResponse;
}> {
  const panels: RagPanel[] = [];

  if (notebookState.rag_configs && notebookState.rag_configs.length > 0) {
    for (const ragConfig of notebookState.rag_configs) {
      if (ragConfig.type === "saved") {
        const savedConfig = ragConfig as { type: "saved" } & SavedRagConfigOutput;
        const panel = await savedConfigToPanel(savedConfig, apiClient);
        if (panel) {
          panels.push(panel);
        }
      } else if (ragConfig.type === "unsaved") {
        const unsavedConfig = ragConfig as { type: "unsaved" } & UnsavedRagConfigResponse;
        const panel = unsavedConfigToPanel(unsavedConfig);
        panels.push(panel);
      }
    }
  }

  if (panels.length === 0) {
    panels.push(createPanel());
  }

  let experimentConfig: RagExperimentConfig | null = null;
  if (notebookState.dataset_ref) {
    experimentConfig = {
      name: "",
      description: "",
      dataset_ref: {
        id: notebookState.dataset_ref.id,
        version: notebookState.dataset_ref.version,
      },
      eval_list:
        notebookState.eval_list?.map((evalRef) => ({
          name: evalRef.name,
          version: evalRef.version,
          variable_mapping: evalRef.variable_mapping.map((vm) => ({
            variable_name: vm.variable_name,
            source: vm.source,
          })),
        })) || [],
      dataset_row_filter: notebookState.dataset_row_filter?.map((f) => ({
        column_name: f.column_name,
        column_value: f.column_value,
      })),
    };
  }

  return { panels, experimentConfig, fullState: notebookState };
}
