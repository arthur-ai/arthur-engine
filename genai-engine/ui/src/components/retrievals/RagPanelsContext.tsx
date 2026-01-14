import React, { createContext, useContext, useReducer, useCallback, useMemo, useState, useEffect, type ReactNode, type Dispatch } from "react";

import {
  ragPanelsReducer,
  createInitialState,
  type RagPanelsState,
  type RagPanelsAction,
  type RagPanel,
  MAX_PANELS,
  MIN_PANELS,
} from "./ragPanelsReducer";
import type { SearchMethod, SearchSettings } from "./types";
import { serializeRagPanelsState, type RagExperimentConfig } from "./utils/ragNotebookStateUtils";

import { useApi } from "@/hooks/useApi";
import { useRagNotebook, useRagNotebookState, useSetRagNotebookStateMutation } from "@/hooks/useRagNotebooks";
import type { RagProviderCollectionResponse, RagProviderQueryResponse, RagNotebookDetail } from "@/lib/api-client/api-client";

type NotebookSyncStatus = { state: "idle" } | { state: "loading" } | { state: "synced" } | { state: "dirty" };

interface LoadPanelConfigPayload {
  panelId: string;
  providerId: string;
  collection: RagProviderCollectionResponse | null;
  method: SearchMethod;
  settings: SearchSettings;
  configId: string;
  configName: string;
  version: number;
}

interface RagPanelsContextValue {
  state: RagPanelsState;
  dispatch: Dispatch<RagPanelsAction>;
  // Notebook state
  notebookId: string | null;
  notebook: RagNotebookDetail | null;
  isLoadingNotebook: boolean;
  notebookError: Error | null;
  isDirty: boolean;
  experimentConfig: RagExperimentConfig | null;
  setExperimentConfig: (config: RagExperimentConfig | null) => void;
  // Convenience methods
  addPanel: (defaultProviderId?: string) => void;
  removePanel: (panelId: string) => void;
  updatePanelProvider: (panelId: string, providerId: string) => void;
  updatePanelCollection: (panelId: string, collection: RagProviderCollectionResponse | null) => void;
  updatePanelMethod: (panelId: string, method: SearchMethod) => void;
  updatePanelSettings: (panelId: string, settings: SearchSettings) => void;
  updatePanelLoadedConfig: (panelId: string, configId: string | null, configName: string | null, version: number | null) => void;
  loadPanelConfig: (payload: LoadPanelConfigPayload) => void;
  setSharedQuery: (query: string) => void;
  runSearchOnPanel: (panel: RagPanel, query: string) => Promise<void>;
  runAllPanels: () => Promise<void>;
  saveNotebookState: () => Promise<void>;
  canAddPanel: boolean;
  canRemovePanel: boolean;
}

const RagPanelsContext = createContext<RagPanelsContextValue | null>(null);

interface RagPanelsProviderProps {
  children: ReactNode;
  defaultProviderId?: string;
  notebookId?: string | null;
}

export const RagPanelsProvider: React.FC<RagPanelsProviderProps> = ({ children, defaultProviderId, notebookId = null }) => {
  const [state, dispatch] = useReducer(ragPanelsReducer, createInitialState(defaultProviderId));
  const [experimentConfig, setExperimentConfigInternal] = useState<RagExperimentConfig | null>(null);
  const [syncStatus, setSyncStatus] = useState<NotebookSyncStatus>({ state: "idle" });

  const api = useApi();

  const { notebook, isLoading: isLoadingNotebookQuery, error: notebookQueryError } = useRagNotebook(notebookId ?? undefined);
  const { panels: loadedPanels, experimentConfig: loadedExperimentConfig, isSuccess: hasLoadedState } = useRagNotebookState(notebookId ?? undefined);
  const setNotebookStateMutation = useSetRagNotebookStateMutation();

  const isDirty = syncStatus.state === "dirty";
  const isLoadingNotebook = syncStatus.state === "loading" || isLoadingNotebookQuery;
  const notebookError = notebookQueryError as Error | null;

  useEffect(() => {
    if (!hasLoadedState || syncStatus.state !== "idle" || !loadedPanels) {
      return;
    }

    dispatch({ type: "hydrateNotebookState", payload: { panels: loadedPanels } });

    if (loadedExperimentConfig) {
      setExperimentConfigInternal(loadedExperimentConfig);
    }

    setSyncStatus({ state: "synced" });
  }, [hasLoadedState, syncStatus.state, loadedPanels, loadedExperimentConfig]);

  useEffect(() => {
    setSyncStatus({ state: "idle" });
  }, [notebookId]);

  const markDirty = useCallback(() => {
    if (notebookId && (syncStatus.state === "synced" || syncStatus.state === "idle")) {
      setSyncStatus({ state: "dirty" });
    }
  }, [notebookId, syncStatus.state]);

  const addPanel = useCallback(
    (providerId?: string) => {
      dispatch({ type: "addPanel", payload: { defaultProviderId: providerId } });
      markDirty();
    },
    [markDirty]
  );

  const removePanel = useCallback(
    (panelId: string) => {
      dispatch({ type: "removePanel", payload: { panelId } });
      markDirty();
    },
    [markDirty]
  );

  const updatePanelProvider = useCallback(
    (panelId: string, providerId: string) => {
      dispatch({ type: "updatePanelProvider", payload: { panelId, providerId } });
      markDirty();
    },
    [markDirty]
  );

  const updatePanelCollection = useCallback(
    (panelId: string, collection: RagProviderCollectionResponse | null) => {
      dispatch({ type: "updatePanelCollection", payload: { panelId, collection } });
      markDirty();
    },
    [markDirty]
  );

  const updatePanelMethod = useCallback(
    (panelId: string, method: SearchMethod) => {
      dispatch({ type: "updatePanelMethod", payload: { panelId, method } });
      markDirty();
    },
    [markDirty]
  );

  const updatePanelSettings = useCallback(
    (panelId: string, settings: SearchSettings) => {
      dispatch({ type: "updatePanelSettings", payload: { panelId, settings } });
      markDirty();
    },
    [markDirty]
  );

  const updatePanelLoadedConfig = useCallback(
    (panelId: string, configId: string | null, configName: string | null, version: number | null) => {
      dispatch({ type: "updatePanelLoadedConfig", payload: { panelId, configId, configName, version } });
      markDirty();
    },
    [markDirty]
  );

  const loadPanelConfig = useCallback(
    (payload: LoadPanelConfigPayload) => {
      dispatch({ type: "loadPanelConfig", payload });
      markDirty();
    },
    [markDirty]
  );

  const setSharedQuery = useCallback(
    (query: string) => {
      dispatch({ type: "setSharedQuery", payload: { query } });
      markDirty();
    },
    [markDirty]
  );

  const setExperimentConfig = useCallback(
    (config: RagExperimentConfig | null) => {
      setExperimentConfigInternal(config);
      markDirty();
    },
    [markDirty]
  );

  const saveNotebookState = useCallback(async () => {
    if (!notebookId) {
      return;
    }

    const serializedState = serializeRagPanelsState(state, experimentConfig ?? undefined);

    await setNotebookStateMutation.mutateAsync({
      notebookId,
      request: { state: serializedState },
    });

    setSyncStatus({ state: "synced" });
  }, [notebookId, setNotebookStateMutation, state, experimentConfig]);

  const runSearchOnPanel = useCallback(
    async (panel: RagPanel, query: string): Promise<void> => {
      if (!api || !panel.providerId || !panel.collection) {
        return;
      }

      dispatch({ type: "setPanelLoading", payload: { panelId: panel.id, isLoading: true } });

      try {
        let response: { data: RagProviderQueryResponse };

        const baseSettings = {
          collection_name: panel.collection.identifier,
          query,
          limit: panel.settings.limit,
          return_properties: panel.settings.includeMetadata ? undefined : [],
          include_vector: panel.settings.includeVector,
          return_metadata: ["distance", "certainty", "score", "explain_score"] as ("distance" | "certainty" | "score" | "explain_score")[],
        };

        if (panel.method === "nearText") {
          response = await api.api.executeSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPost(panel.providerId, {
            settings: {
              ...baseSettings,
              certainty: 1 - panel.settings.distance,
            },
          });
        } else if (panel.method === "bm25") {
          response = await api.api.executeKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPost(panel.providerId, {
            settings: baseSettings,
          });
        } else {
          // hybrid
          response = await api.api.executeHybridSearchApiV1RagProvidersProviderIdHybridSearchPost(panel.providerId, {
            settings: {
              ...baseSettings,
              alpha: panel.settings.alpha,
            },
          });
        }

        dispatch({
          type: "setPanelResults",
          payload: { panelId: panel.id, results: response.data.response, error: null },
        });
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Search failed";
        dispatch({
          type: "setPanelResults",
          payload: { panelId: panel.id, results: null, error: errorMessage },
        });
      }
    },
    [api]
  );

  const runAllPanels = useCallback(async () => {
    const query = state.sharedQuery.trim();
    if (!query) return;

    dispatch({ type: "setRunningAll", payload: { isRunning: true } });

    // Filter panels that are ready to search
    const readyPanels = state.panels.filter((panel) => panel.providerId && panel.collection);

    // Run all searches in parallel
    await Promise.all(readyPanels.map((panel) => runSearchOnPanel(panel, query)));

    dispatch({ type: "setRunningAll", payload: { isRunning: false } });
  }, [state.sharedQuery, state.panels, runSearchOnPanel]);

  const canAddPanel = state.panels.length < MAX_PANELS;
  const canRemovePanel = state.panels.length > MIN_PANELS;

  const value = useMemo<RagPanelsContextValue>(
    () => ({
      state,
      dispatch,
      notebookId,
      notebook: notebook ?? null,
      isLoadingNotebook,
      notebookError,
      isDirty,
      experimentConfig,
      setExperimentConfig,
      addPanel,
      removePanel,
      updatePanelProvider,
      updatePanelCollection,
      updatePanelMethod,
      updatePanelSettings,
      updatePanelLoadedConfig,
      loadPanelConfig,
      setSharedQuery,
      runSearchOnPanel,
      runAllPanels,
      saveNotebookState,
      canAddPanel,
      canRemovePanel,
    }),
    [
      state,
      notebookId,
      notebook,
      isLoadingNotebook,
      notebookError,
      isDirty,
      experimentConfig,
      setExperimentConfig,
      addPanel,
      removePanel,
      updatePanelProvider,
      updatePanelCollection,
      updatePanelMethod,
      updatePanelSettings,
      updatePanelLoadedConfig,
      loadPanelConfig,
      setSharedQuery,
      runSearchOnPanel,
      runAllPanels,
      saveNotebookState,
      canAddPanel,
      canRemovePanel,
    ]
  );

  return <RagPanelsContext.Provider value={value}>{children}</RagPanelsContext.Provider>;
};

export function useRagPanels(): RagPanelsContextValue {
  const context = useContext(RagPanelsContext);
  if (!context) {
    throw new Error("useRagPanels must be used within a RagPanelsProvider");
  }
  return context;
}
