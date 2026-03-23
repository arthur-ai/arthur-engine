import type { UseMutationResult } from "@tanstack/react-query";

import type { DatasetResponse, DatasetVersionResponse, DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import type { ColumnDefaults } from "@/types/dataset";

export interface PendingChanges {
  added: DatasetVersionRowResponse[];
  updated: DatasetVersionRowResponse[];
  deleted: string[];
}

export interface DatasetState {
  columns: string[];
  rows: DatasetVersionRowResponse[];
  columnDefaults: ColumnDefaults;
  pendingChanges: PendingChanges;

  selectedVersion: number | undefined;

  pagination: {
    page: number;
    rowsPerPage: number;
  };
  sorting: {
    column: string | null;
    direction: "asc" | "desc";
  };
  searchQuery: string;

  modals: {
    edit: { open: boolean; row: DatasetVersionRowResponse | null };
    add: boolean;
    configure: boolean;
    import: boolean;
    fill: { open: boolean; columnName: string | null };
    synthetic: boolean;
  };
  versionDrawerOpen: boolean;
  confirmation: {
    type: "unsavedNavigation" | "unsavedVersionSwitch" | "unsavedFillColumn" | null;
    targetVersion: number | null;
    targetColumn: string | null;
  };
}

export type DatasetAction =
  | { type: "DATA/LOAD_VERSION"; payload: DatasetVersionResponse }
  | { type: "DATA/SET_COLUMNS"; payload: string[] }
  | { type: "DATA/SET_COLUMN_DEFAULTS"; payload: ColumnDefaults }
  | { type: "DATA/ADD_ROW"; payload: Record<string, unknown> }
  | { type: "DATA/UPDATE_ROW"; payload: { id: string; data: Record<string, unknown> } }
  | { type: "DATA/DELETE_ROW"; payload: string }
  | { type: "DATA/CLEAR_CHANGES" }
  | { type: "DATA/IMPORT_ROWS"; payload: { columns: string[]; rows: Record<string, string>[] } }
  | { type: "VERSION/SELECT"; payload: number }
  | { type: "VERSION/RESET_TO_LATEST" }
  | { type: "VIEW/SET_PAGE"; payload: number }
  | { type: "VIEW/SET_ROWS_PER_PAGE"; payload: number }
  | { type: "VIEW/TOGGLE_SORT"; payload: string }
  | { type: "VIEW/SET_SEARCH"; payload: string }
  | { type: "VIEW/RESET_PAGINATION" }
  | { type: "UI/OPEN_EDIT_MODAL"; payload: DatasetVersionRowResponse }
  | { type: "UI/CLOSE_EDIT_MODAL" }
  | { type: "UI/TOGGLE_ADD_MODAL"; payload: boolean }
  | { type: "UI/TOGGLE_CONFIGURE_MODAL"; payload: boolean }
  | { type: "UI/TOGGLE_IMPORT_MODAL"; payload: boolean }
  | { type: "UI/OPEN_FILL_MODAL"; payload: string }
  | { type: "UI/CLOSE_FILL_MODAL" }
  | { type: "UI/TOGGLE_SYNTHETIC_MODAL"; payload: boolean }
  | { type: "UI/TOGGLE_VERSION_DRAWER"; payload: boolean }
  | {
      type: "UI/SHOW_CONFIRMATION";
      payload: { type: "unsavedNavigation" | "unsavedVersionSwitch" | "unsavedFillColumn"; targetVersion?: number; targetColumn?: string };
    }
  | { type: "UI/HIDE_CONFIRMATION" };

export interface UseDatasetQueriesReturn {
  dataset: DatasetResponse | undefined;
  datasetLoading: boolean;
  datasetError: Error | null;
  refetchDataset: () => void;

  latestVersion: number | undefined;
  latestVersionLoading: boolean;

  versionData: DatasetVersionResponse | undefined;
  versionLoading: boolean;
  versionError: Error | null;

  currentVersion: number | undefined;
  isLoading: boolean;
  totalRowCount: number;
}

export interface DatasetUpdateParams {
  name: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export interface UseDatasetMutationsReturn {
  save: UseMutationResult<void, Error, void>;
  fillColumn: UseMutationResult<void, Error, { columnName: string; value: string }>;
  applyDefaults: UseMutationResult<void, Error, { columnDefaults: ColumnDefaults }>;
  updateDataset: UseMutationResult<void, Error, DatasetUpdateParams>;
}

export interface DatasetContextValue {
  state: DatasetState;
  dispatch: React.Dispatch<DatasetAction>;
  queries: UseDatasetQueriesReturn;
  mutations: UseDatasetMutationsReturn;
  showSnackbar: (message: string, severity: "success" | "error" | "warning" | "info") => void;
}

export const initialDatasetState: DatasetState = {
  columns: [],
  rows: [],
  columnDefaults: {},
  pendingChanges: { added: [], updated: [], deleted: [] },

  selectedVersion: undefined,

  pagination: { page: 0, rowsPerPage: 25 },
  sorting: { column: null, direction: "asc" },
  searchQuery: "",

  modals: {
    edit: { open: false, row: null },
    add: false,
    configure: false,
    import: false,
    fill: { open: false, columnName: null },
    synthetic: false,
  },
  versionDrawerOpen: false,
  confirmation: { type: null, targetVersion: null, targetColumn: null },
};
