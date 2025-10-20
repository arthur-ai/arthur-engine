import { useEffect, useMemo, useReducer } from "react";

import { DatasetVersionResponse } from "@/lib/api-client/api-client";
import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { generateTempRowId } from "@/utils/datasetRowUtils";

export interface PendingChanges {
  added: DatasetVersionRowResponse[];
  updated: DatasetVersionRowResponse[];
  deleted: string[];
}

interface DatasetState {
  columns: string[];
  rows: DatasetVersionRowResponse[];
  pendingChanges: PendingChanges;
}

type DatasetAction =
  | { type: "LOAD_VERSION"; payload: DatasetVersionResponse }
  | { type: "SET_COLUMNS"; payload: string[] }
  | { type: "ADD_ROW"; payload: Record<string, unknown> }
  | {
      type: "UPDATE_ROW";
      payload: { id: string; rowData: Record<string, unknown> };
    }
  | { type: "DELETE_ROW"; payload: string }
  | { type: "CLEAR_CHANGES" };

function createRowFromData(
  columns: string[],
  rowData: Record<string, unknown>,
  rowId?: string
): DatasetVersionRowResponse {
  return {
    id: rowId || generateTempRowId(),
    data: columns.map((column_name) => ({
      column_name,
      column_value: String(rowData[column_name] ?? ""),
    })),
  };
}

function transformRowsForNewColumns(
  rows: DatasetVersionRowResponse[],
  oldColumns: string[],
  newColumns: string[]
): DatasetVersionRowResponse[] {
  return rows.map((row) => ({
    id: row.id,
    data: newColumns.map((newColName, idx) => {
      const oldColName = oldColumns[idx];
      let columnValue = "";

      if (oldColName) {
        const existing = row.data.find((d) => d.column_name === oldColName);
        columnValue = existing?.column_value || "";
      } else {
        const existing = row.data.find((d) => d.column_name === newColName);
        columnValue = existing?.column_value || "";
      }

      return {
        column_name: newColName,
        column_value: columnValue,
      };
    }),
  }));
}

function datasetReducer(
  state: DatasetState,
  action: DatasetAction
): DatasetState {
  switch (action.type) {
    case "LOAD_VERSION": {
      return {
        columns: action.payload.column_names,
        rows: action.payload.rows,
        pendingChanges: { added: [], updated: [], deleted: [] },
      };
    }

    case "SET_COLUMNS": {
      const newColumns = action.payload;
      const oldColumns = state.columns;

      const oldColumnsSet = new Set(oldColumns);
      const newColumnsSet = new Set(newColumns);

      const columnsAdded =
        newColumns.filter((col) => !oldColumnsSet.has(col)).length > 0;
      const columnsRemoved =
        oldColumns.filter((col) => !newColumnsSet.has(col)).length > 0;
      const columnsRenamed = newColumns.some(
        (col, idx) => oldColumns[idx] && oldColumns[idx] !== col
      );

      if (
        !columnsRemoved &&
        !columnsRenamed &&
        (!columnsAdded || state.rows.length === 0)
      ) {
        return {
          ...state,
          columns: newColumns,
        };
      }

      const transformedRows = transformRowsForNewColumns(
        state.rows,
        oldColumns,
        newColumns
      );

      const updatedRowIds = new Set(
        state.pendingChanges.updated.map((r) => r.id)
      );
      const addedRowIds = new Set(state.pendingChanges.added.map((r) => r.id));

      const rowsToUpdate = transformedRows.filter(
        (row) => !updatedRowIds.has(row.id) && !addedRowIds.has(row.id)
      );

      return {
        ...state,
        columns: newColumns,
        rows: transformedRows,
        pendingChanges: {
          ...state.pendingChanges,
          updated: [...state.pendingChanges.updated, ...rowsToUpdate],
        },
      };
    }

    case "ADD_ROW": {
      const newRow = createRowFromData(state.columns, action.payload);

      return {
        ...state,
        rows: [...state.rows, newRow],
        pendingChanges: {
          ...state.pendingChanges,
          added: [...state.pendingChanges.added, newRow],
        },
      };
    }

    case "UPDATE_ROW": {
      const { id, rowData } = action.payload;
      const updatedRow = createRowFromData(state.columns, rowData, id);

      const isNewRow = state.pendingChanges.added.some((r) => r.id === id);

      if (isNewRow) {
        return {
          ...state,
          rows: state.rows.map((row) => (row.id === id ? updatedRow : row)),
          pendingChanges: {
            ...state.pendingChanges,
            added: state.pendingChanges.added.map((r) =>
              r.id === id ? updatedRow : r
            ),
          },
        };
      }

      const alreadyTracked = state.pendingChanges.updated.some(
        (r) => r.id === id
      );

      return {
        ...state,
        rows: state.rows.map((row) => (row.id === id ? updatedRow : row)),
        pendingChanges: {
          ...state.pendingChanges,
          updated: alreadyTracked
            ? state.pendingChanges.updated.map((r) =>
                r.id === id ? updatedRow : r
              )
            : [...state.pendingChanges.updated, updatedRow],
        },
      };
    }

    case "DELETE_ROW": {
      const rowId = action.payload;
      const isNewRow = state.pendingChanges.added.some((r) => r.id === rowId);

      if (isNewRow) {
        return {
          ...state,
          rows: state.rows.filter((row) => row.id !== rowId),
          pendingChanges: {
            ...state.pendingChanges,
            added: state.pendingChanges.added.filter((r) => r.id !== rowId),
          },
        };
      }

      return {
        ...state,
        rows: state.rows.filter((row) => row.id !== rowId),
        pendingChanges: {
          ...state.pendingChanges,
          deleted: [...state.pendingChanges.deleted, rowId],
          updated: state.pendingChanges.updated.filter((r) => r.id !== rowId),
        },
      };
    }

    case "CLEAR_CHANGES": {
      return {
        ...state,
        pendingChanges: { added: [], updated: [], deleted: [] },
      };
    }

    default:
      return state;
  }
}

const initialState: DatasetState = {
  columns: [],
  rows: [],
  pendingChanges: { added: [], updated: [], deleted: [] },
};

export interface UseDatasetLocalStateReturn {
  localColumns: string[];
  localRows: DatasetVersionRowResponse[];
  pendingChanges: PendingChanges;
  hasUnsavedChanges: boolean;

  setColumns: (columns: string[]) => void;
  addRow: (rowData: Record<string, unknown>) => void;
  updateRow: (id: string, rowData: Record<string, unknown>) => void;
  deleteRow: (id: string) => void;
  clearChanges: () => void;
}

export function useDatasetLocalState(
  versionData: DatasetVersionResponse | undefined
): UseDatasetLocalStateReturn {
  const [state, dispatch] = useReducer(datasetReducer, initialState);

  useEffect(() => {
    if (versionData) {
      dispatch({ type: "LOAD_VERSION", payload: versionData });
    }
  }, [versionData]);

  const hasUnsavedChanges = useMemo(() => {
    return (
      state.pendingChanges.added.length > 0 ||
      state.pendingChanges.updated.length > 0 ||
      state.pendingChanges.deleted.length > 0
    );
  }, [state.pendingChanges]);

  return {
    localColumns: state.columns,
    localRows: state.rows,
    pendingChanges: state.pendingChanges,
    hasUnsavedChanges,
    setColumns: (columns: string[]) =>
      dispatch({ type: "SET_COLUMNS", payload: columns }),
    addRow: (rowData: Record<string, unknown>) =>
      dispatch({ type: "ADD_ROW", payload: rowData }),
    updateRow: (id: string, rowData: Record<string, unknown>) =>
      dispatch({ type: "UPDATE_ROW", payload: { id, rowData } }),
    deleteRow: (id: string) => dispatch({ type: "DELETE_ROW", payload: id }),
    clearChanges: () => dispatch({ type: "CLEAR_CHANGES" }),
  };
}
