import type { DatasetAction } from "./types";

import type { DatasetVersionResponse, DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import type { ColumnDefaults } from "@/types/dataset";

export const datasetActions = {
  loadVersion: (payload: DatasetVersionResponse): DatasetAction => ({
    type: "DATA/LOAD_VERSION",
    payload,
  }),

  setColumns: (columns: string[]): DatasetAction => ({
    type: "DATA/SET_COLUMNS",
    payload: columns,
  }),

  setColumnDefaults: (defaults: ColumnDefaults): DatasetAction => ({
    type: "DATA/SET_COLUMN_DEFAULTS",
    payload: defaults,
  }),

  addRow: (rowData: Record<string, unknown>): DatasetAction => ({
    type: "DATA/ADD_ROW",
    payload: rowData,
  }),

  updateRow: (id: string, data: Record<string, unknown>): DatasetAction => ({
    type: "DATA/UPDATE_ROW",
    payload: { id, data },
  }),

  deleteRow: (id: string): DatasetAction => ({
    type: "DATA/DELETE_ROW",
    payload: id,
  }),

  clearChanges: (): DatasetAction => ({
    type: "DATA/CLEAR_CHANGES",
  }),

  importRows: (columns: string[], rows: Record<string, string>[]): DatasetAction => ({
    type: "DATA/IMPORT_ROWS",
    payload: { columns, rows },
  }),

  selectVersion: (versionNumber: number): DatasetAction => ({
    type: "VERSION/SELECT",
    payload: versionNumber,
  }),

  resetToLatest: (): DatasetAction => ({
    type: "VERSION/RESET_TO_LATEST",
  }),

  setPage: (page: number): DatasetAction => ({
    type: "VIEW/SET_PAGE",
    payload: page,
  }),

  setRowsPerPage: (rowsPerPage: number): DatasetAction => ({
    type: "VIEW/SET_ROWS_PER_PAGE",
    payload: rowsPerPage,
  }),

  toggleSort: (column: string): DatasetAction => ({
    type: "VIEW/TOGGLE_SORT",
    payload: column,
  }),

  setSearch: (query: string): DatasetAction => ({
    type: "VIEW/SET_SEARCH",
    payload: query,
  }),

  resetPagination: (): DatasetAction => ({
    type: "VIEW/RESET_PAGINATION",
  }),

  openEditModal: (row: DatasetVersionRowResponse): DatasetAction => ({
    type: "UI/OPEN_EDIT_MODAL",
    payload: row,
  }),

  closeEditModal: (): DatasetAction => ({
    type: "UI/CLOSE_EDIT_MODAL",
  }),

  toggleAddModal: (open: boolean): DatasetAction => ({
    type: "UI/TOGGLE_ADD_MODAL",
    payload: open,
  }),

  toggleConfigureModal: (open: boolean): DatasetAction => ({
    type: "UI/TOGGLE_CONFIGURE_MODAL",
    payload: open,
  }),

  toggleImportModal: (open: boolean): DatasetAction => ({
    type: "UI/TOGGLE_IMPORT_MODAL",
    payload: open,
  }),

  openFillModal: (columnName: string): DatasetAction => ({
    type: "UI/OPEN_FILL_MODAL",
    payload: columnName,
  }),

  closeFillModal: (): DatasetAction => ({
    type: "UI/CLOSE_FILL_MODAL",
  }),

  toggleVersionDrawer: (open: boolean): DatasetAction => ({
    type: "UI/TOGGLE_VERSION_DRAWER",
    payload: open,
  }),

  showConfirmation: (
    type: "unsavedNavigation" | "unsavedVersionSwitch" | "unsavedFillColumn",
    targetVersion?: number,
    targetColumn?: string
  ): DatasetAction => ({
    type: "UI/SHOW_CONFIRMATION",
    payload: { type, targetVersion, targetColumn },
  }),

  hideConfirmation: (): DatasetAction => ({
    type: "UI/HIDE_CONFIRMATION",
  }),
};
