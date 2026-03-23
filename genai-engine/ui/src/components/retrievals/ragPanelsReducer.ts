import { v4 as uuidv4 } from "uuid";

import type { SearchMethod, SearchSettings } from "./types";

import { DEFAULT_SEARCH_SETTINGS } from "@/constants/search";
import type { RagProviderCollectionResponse, WeaviateQueryResults } from "@/lib/api-client/api-client";

export interface RagPanel {
  id: string;
  providerId: string;
  collection: RagProviderCollectionResponse | null;
  method: SearchMethod;
  settings: SearchSettings;
  loadedConfigId: string | null;
  loadedConfigName: string | null;
  loadedVersion: number | null;
  results: WeaviateQueryResults | null;
  isLoading: boolean;
  error: string | null;
}

export interface RagPanelsState {
  panels: RagPanel[];
  sharedQuery: string;
  isRunningAll: boolean;
}

export type RagPanelsAction =
  | { type: "addPanel"; payload?: { defaultProviderId?: string } }
  | { type: "removePanel"; payload: { panelId: string } }
  | { type: "updatePanelProvider"; payload: { panelId: string; providerId: string } }
  | { type: "updatePanelCollection"; payload: { panelId: string; collection: RagProviderCollectionResponse | null } }
  | { type: "updatePanelMethod"; payload: { panelId: string; method: SearchMethod } }
  | { type: "updatePanelSettings"; payload: { panelId: string; settings: SearchSettings } }
  | { type: "updatePanelLoadedConfig"; payload: { panelId: string; configId: string | null; configName: string | null; version: number | null } }
  | { type: "setPanelLoading"; payload: { panelId: string; isLoading: boolean } }
  | { type: "setPanelResults"; payload: { panelId: string; results: WeaviateQueryResults | null; error: string | null } }
  | { type: "setSharedQuery"; payload: { query: string } }
  | { type: "setRunningAll"; payload: { isRunning: boolean } }
  | {
      type: "loadPanelConfig";
      payload: {
        panelId: string;
        providerId: string;
        collection: RagProviderCollectionResponse | null;
        method: SearchMethod;
        settings: SearchSettings;
        configId: string;
        configName: string;
        version: number;
      };
    }
  | { type: "hydrateNotebookState"; payload: { panels: RagPanel[] } };

export const MIN_PANELS = 1;
export const MAX_PANELS = 4;

export const createPanel = (defaultProviderId?: string): RagPanel => ({
  id: uuidv4(),
  providerId: defaultProviderId || "",
  collection: null,
  method: "nearText",
  settings: { ...DEFAULT_SEARCH_SETTINGS },
  loadedConfigId: null,
  loadedConfigName: null,
  loadedVersion: null,
  results: null,
  isLoading: false,
  error: null,
});

export const createInitialState = (defaultProviderId?: string): RagPanelsState => ({
  panels: [createPanel(defaultProviderId)],
  sharedQuery: "",
  isRunningAll: false,
});

export function ragPanelsReducer(state: RagPanelsState, action: RagPanelsAction): RagPanelsState {
  switch (action.type) {
    case "addPanel": {
      if (state.panels.length >= MAX_PANELS) {
        return state;
      }
      const newPanel = createPanel(action.payload?.defaultProviderId);
      return {
        ...state,
        panels: [...state.panels, newPanel],
      };
    }

    case "removePanel": {
      if (state.panels.length <= MIN_PANELS) {
        return state;
      }
      return {
        ...state,
        panels: state.panels.filter((panel) => panel.id !== action.payload.panelId),
      };
    }

    case "updatePanelProvider": {
      return {
        ...state,
        panels: state.panels.map((panel) =>
          panel.id === action.payload.panelId
            ? { ...panel, providerId: action.payload.providerId, collection: null, results: null, error: null }
            : panel
        ),
      };
    }

    case "updatePanelCollection": {
      return {
        ...state,
        panels: state.panels.map((panel) =>
          panel.id === action.payload.panelId ? { ...panel, collection: action.payload.collection, results: null, error: null } : panel
        ),
      };
    }

    case "updatePanelMethod": {
      return {
        ...state,
        panels: state.panels.map((panel) => (panel.id === action.payload.panelId ? { ...panel, method: action.payload.method } : panel)),
      };
    }

    case "updatePanelSettings": {
      return {
        ...state,
        panels: state.panels.map((panel) => (panel.id === action.payload.panelId ? { ...panel, settings: action.payload.settings } : panel)),
      };
    }

    case "updatePanelLoadedConfig": {
      return {
        ...state,
        panels: state.panels.map((panel) =>
          panel.id === action.payload.panelId
            ? {
                ...panel,
                loadedConfigId: action.payload.configId,
                loadedConfigName: action.payload.configName,
                loadedVersion: action.payload.version,
              }
            : panel
        ),
      };
    }

    case "loadPanelConfig": {
      return {
        ...state,
        panels: state.panels.map((panel) =>
          panel.id === action.payload.panelId
            ? {
                ...panel,
                providerId: action.payload.providerId,
                collection: action.payload.collection,
                method: action.payload.method,
                settings: action.payload.settings,
                loadedConfigId: action.payload.configId,
                loadedConfigName: action.payload.configName,
                loadedVersion: action.payload.version,
                results: null,
                error: null,
              }
            : panel
        ),
      };
    }

    case "setPanelLoading": {
      return {
        ...state,
        panels: state.panels.map((panel) => (panel.id === action.payload.panelId ? { ...panel, isLoading: action.payload.isLoading } : panel)),
      };
    }

    case "setPanelResults": {
      return {
        ...state,
        panels: state.panels.map((panel) =>
          panel.id === action.payload.panelId ? { ...panel, results: action.payload.results, error: action.payload.error, isLoading: false } : panel
        ),
      };
    }

    case "setSharedQuery": {
      return {
        ...state,
        sharedQuery: action.payload.query,
      };
    }

    case "setRunningAll": {
      return {
        ...state,
        isRunningAll: action.payload.isRunning,
      };
    }

    case "hydrateNotebookState": {
      return {
        ...state,
        panels: action.payload.panels.length > 0 ? action.payload.panels : [createPanel()],
      };
    }

    default:
      return state;
  }
}
