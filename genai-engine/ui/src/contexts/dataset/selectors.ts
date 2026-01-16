import type { DatasetState } from "./types";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { convertFromApiFormat } from "@/utils/datasetRowUtils";
import { sortRows } from "@/utils/datasetSortUtils";
import { createEmptyRow } from "@/utils/datasetUtils";

export function selectSortedRows(state: DatasetState): DatasetVersionRowResponse[] {
  return sortRows(state.rows, state.sorting.column, state.sorting.direction);
}

export function selectFilteredRows(state: DatasetState): DatasetVersionRowResponse[] {
  const sorted = selectSortedRows(state);

  if (!state.searchQuery.trim()) {
    return sorted;
  }

  const lower = state.searchQuery.toLowerCase();
  return sorted.filter((row) => row.data.some((col) => col.column_value?.toLowerCase().includes(lower)));
}

export function selectHasUnsavedChanges(state: DatasetState): boolean {
  const { added, updated, deleted } = state.pendingChanges;
  return added.length > 0 || updated.length > 0 || deleted.length > 0;
}

export function selectPendingChangesCounts(state: DatasetState): {
  added: number;
  updated: number;
  deleted: number;
  total: number;
} {
  const { added, updated, deleted } = state.pendingChanges;
  return {
    added: added.length,
    updated: updated.length,
    deleted: deleted.length,
    total: added.length + updated.length + deleted.length,
  };
}

export function selectAddRowData(state: DatasetState): Record<string, string> {
  return createEmptyRow(state.columns, state.columnDefaults);
}

export function selectEditRowData(state: DatasetState): Record<string, unknown> {
  if (!state.modals.edit.row) {
    return {};
  }

  const existing = convertFromApiFormat(state.modals.edit.row);
  const empty = createEmptyRow(state.columns);

  return { ...empty, ...existing };
}

export function selectHasOpenModal(state: DatasetState): boolean {
  return state.modals.edit.open || state.modals.add || state.modals.configure || state.modals.import || state.modals.fill.open;
}

export function selectHasActiveConfirmation(state: DatasetState): boolean {
  return state.confirmation.type !== null;
}

export function selectCanSave(state: DatasetState): boolean {
  return selectHasUnsavedChanges(state);
}

export function selectCanAddRow(state: DatasetState): boolean {
  return state.columns.length > 0;
}
