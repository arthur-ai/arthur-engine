import { Alert, Snackbar } from "@mui/material";
import React, { createContext, useEffect, useReducer } from "react";

import { datasetReducer } from "./reducer";
import { selectHasUnsavedChanges } from "./selectors";
import type { DatasetContextValue } from "./types";
import { initialDatasetState } from "./types";
import { useDatasetMutations } from "./useDatasetMutations";
import { useDatasetQueries } from "./useDatasetQueries";

import { SEARCH_DEBOUNCE_MS } from "@/constants/datasetConstants";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import useSnackbar from "@/hooks/useSnackbar";
import type { ColumnDefaults } from "@/types/dataset";

export const DatasetContext = createContext<DatasetContextValue | null>(null);

interface DatasetContextProviderProps {
  datasetId: string;
  children: React.ReactNode;
}

export function DatasetContextProvider({ datasetId, children }: DatasetContextProviderProps) {
  const [state, dispatch] = useReducer(datasetReducer, initialDatasetState);
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();
  const debouncedSearchQuery = useDebouncedValue(state.searchQuery, SEARCH_DEBOUNCE_MS);

  const queries = useDatasetQueries({
    datasetId,
    selectedVersion: state.selectedVersion,
    page: state.pagination.page,
    rowsPerPage: state.pagination.rowsPerPage,
    searchQuery: debouncedSearchQuery,
  });

  const hasUnsavedChanges = selectHasUnsavedChanges(state);

  const mutations = useDatasetMutations({
    datasetId,
    currentVersion: queries.currentVersion,
    pendingChanges: state.pendingChanges,
    hasUnsavedChanges,
    dispatch,
    showSnackbar,
  });

  useEffect(() => {
    if (queries.versionData) {
      dispatch({ type: "DATA/LOAD_VERSION", payload: queries.versionData });
    }
  }, [queries.versionData]);

  useEffect(() => {
    const metadata = queries.dataset?.metadata as { columnDefaults?: ColumnDefaults } | null;
    const defaults = metadata?.columnDefaults ?? {};
    dispatch({ type: "DATA/SET_COLUMN_DEFAULTS", payload: defaults });
  }, [queries.dataset?.metadata]);

  const contextValue: DatasetContextValue = {
    state,
    dispatch,
    queries,
    mutations,
    showSnackbar,
  };

  return (
    <DatasetContext.Provider value={contextValue}>
      {children}
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </DatasetContext.Provider>
  );
}
