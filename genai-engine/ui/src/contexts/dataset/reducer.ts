import type { DatasetAction, DatasetState } from "./types";
import { initialDatasetState } from "./types";

import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { generateTempRowId } from "@/utils/datasetRowUtils";

function createRowFromData(columns: string[], rowData: Record<string, unknown>, rowId?: string): DatasetVersionRowResponse {
  return {
    id: rowId || generateTempRowId(),
    created_at: Date.now(),
    data: columns.map((column_name) => ({
      column_name,
      column_value: String(rowData[column_name] ?? ""),
    })),
  };
}

function transformRowsForNewColumns(rows: DatasetVersionRowResponse[], oldColumns: string[], newColumns: string[]): DatasetVersionRowResponse[] {
  return rows.map((row) => {
    const existingMap = Object.fromEntries(row.data.map((d) => [d.column_name, d.column_value]));

    const result = newColumns.map((newColName, idx) => {
      const oldColName = oldColumns[idx];
      const value = existingMap[newColName] ?? existingMap[oldColName] ?? "";

      return {
        column_name: newColName,
        column_value: value,
      };
    });

    return {
      id: row.id,
      created_at: row.created_at,
      data: result,
    };
  });
}

export function datasetReducer(state: DatasetState, action: DatasetAction): DatasetState {
  switch (action.type) {
    case "DATA/LOAD_VERSION": {
      return {
        ...state,
        columns: action.payload.column_names,
        rows: action.payload.rows,
        pendingChanges: { added: [], updated: [], deleted: [] },
      };
    }

    case "DATA/SET_COLUMNS": {
      const newColumns = action.payload;
      const oldColumns = state.columns;

      const oldColumnsSet = new Set(oldColumns);
      const newColumnsSet = new Set(newColumns);

      const columnsAdded = newColumns.filter((col) => !oldColumnsSet.has(col)).length > 0;
      const columnsRemoved = oldColumns.filter((col) => !newColumnsSet.has(col)).length > 0;
      const columnsRenamed = newColumns.some((col, idx) => oldColumns[idx] && oldColumns[idx] !== col);

      if (!columnsRemoved && !columnsRenamed && (!columnsAdded || state.rows.length === 0)) {
        return {
          ...state,
          columns: newColumns,
        };
      }

      const transformedRows = transformRowsForNewColumns(state.rows, oldColumns, newColumns);

      const updatedRowIds = new Set(state.pendingChanges.updated.map((r) => r.id));
      const addedRowIds = new Set(state.pendingChanges.added.map((r) => r.id));

      const rowsToUpdate = transformedRows.filter((row) => !updatedRowIds.has(row.id) && !addedRowIds.has(row.id));

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

    case "DATA/SET_COLUMN_DEFAULTS": {
      return {
        ...state,
        columnDefaults: action.payload,
      };
    }

    case "DATA/ADD_ROW": {
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

    case "DATA/UPDATE_ROW": {
      const { id, data: rowData } = action.payload;
      const updatedRow = createRowFromData(state.columns, rowData, id);

      const isNewRow = state.pendingChanges.added.some((r) => r.id === id);

      if (isNewRow) {
        return {
          ...state,
          rows: state.rows.map((row) => (row.id === id ? updatedRow : row)),
          pendingChanges: {
            ...state.pendingChanges,
            added: state.pendingChanges.added.map((r) => (r.id === id ? updatedRow : r)),
          },
        };
      }

      const alreadyTracked = state.pendingChanges.updated.some((r) => r.id === id);

      return {
        ...state,
        rows: state.rows.map((row) => (row.id === id ? updatedRow : row)),
        pendingChanges: {
          ...state.pendingChanges,
          updated: alreadyTracked
            ? state.pendingChanges.updated.map((r) => (r.id === id ? updatedRow : r))
            : [...state.pendingChanges.updated, updatedRow],
        },
      };
    }

    case "DATA/DELETE_ROW": {
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

    case "DATA/CLEAR_CHANGES": {
      return {
        ...state,
        pendingChanges: { added: [], updated: [], deleted: [] },
      };
    }

    case "DATA/IMPORT_ROWS": {
      const { columns: csvColumns, rows: csvRows } = action.payload;

      const existingColumnsSet = new Set(state.columns);
      const newColumns = csvColumns.filter((col) => !existingColumnsSet.has(col));
      const mergedColumns = [...state.columns, ...newColumns];

      let newState = state;
      if (newColumns.length > 0) {
        newState = {
          ...newState,
          columns: mergedColumns,
        };
      }

      const newRows: DatasetVersionRowResponse[] = [];
      const newAddedRows: DatasetVersionRowResponse[] = [];

      csvRows.forEach((rowData) => {
        const completeRowData: Record<string, unknown> = {};
        mergedColumns.forEach((col) => {
          completeRowData[col] = rowData[col] ?? "";
        });
        const newRow = createRowFromData(mergedColumns, completeRowData);
        newRows.push(newRow);
        newAddedRows.push(newRow);
      });

      return {
        ...newState,
        rows: [...newState.rows, ...newRows],
        pendingChanges: {
          ...newState.pendingChanges,
          added: [...newState.pendingChanges.added, ...newAddedRows],
        },
      };
    }

    case "VERSION/SELECT": {
      return {
        ...state,
        selectedVersion: action.payload,
        pagination: { ...state.pagination, page: 0 },
      };
    }

    case "VERSION/RESET_TO_LATEST": {
      return {
        ...state,
        selectedVersion: undefined,
      };
    }

    case "VIEW/SET_PAGE": {
      return {
        ...state,
        pagination: { ...state.pagination, page: action.payload },
      };
    }

    case "VIEW/SET_ROWS_PER_PAGE": {
      return {
        ...state,
        pagination: { page: 0, rowsPerPage: action.payload },
      };
    }

    case "VIEW/TOGGLE_SORT": {
      const column = action.payload;
      if (state.sorting.column === column) {
        return {
          ...state,
          sorting: {
            column,
            direction: state.sorting.direction === "asc" ? "desc" : "asc",
          },
        };
      }
      return {
        ...state,
        sorting: { column, direction: "asc" },
      };
    }

    case "VIEW/SET_SEARCH": {
      return {
        ...state,
        searchQuery: action.payload,
      };
    }

    case "VIEW/RESET_PAGINATION": {
      return {
        ...state,
        pagination: { ...state.pagination, page: 0 },
      };
    }

    case "UI/OPEN_EDIT_MODAL": {
      return {
        ...state,
        modals: {
          ...state.modals,
          edit: { open: true, row: action.payload },
        },
      };
    }

    case "UI/CLOSE_EDIT_MODAL": {
      return {
        ...state,
        modals: {
          ...state.modals,
          edit: { open: false, row: null },
        },
      };
    }

    case "UI/TOGGLE_ADD_MODAL": {
      return {
        ...state,
        modals: {
          ...state.modals,
          add: action.payload,
        },
      };
    }

    case "UI/TOGGLE_CONFIGURE_MODAL": {
      return {
        ...state,
        modals: {
          ...state.modals,
          configure: action.payload,
        },
      };
    }

    case "UI/TOGGLE_IMPORT_MODAL": {
      return {
        ...state,
        modals: {
          ...state.modals,
          import: action.payload,
        },
      };
    }

    case "UI/OPEN_FILL_MODAL": {
      return {
        ...state,
        modals: {
          ...state.modals,
          fill: { open: true, columnName: action.payload },
        },
      };
    }

    case "UI/CLOSE_FILL_MODAL": {
      return {
        ...state,
        modals: {
          ...state.modals,
          fill: { open: false, columnName: null },
        },
      };
    }

    case "UI/TOGGLE_VERSION_DRAWER": {
      return {
        ...state,
        versionDrawerOpen: action.payload,
      };
    }

    case "UI/SHOW_CONFIRMATION": {
      return {
        ...state,
        confirmation: {
          type: action.payload.type,
          targetVersion: action.payload.targetVersion ?? null,
          targetColumn: action.payload.targetColumn ?? null,
        },
      };
    }

    case "UI/HIDE_CONFIRMATION": {
      return {
        ...state,
        confirmation: { type: null, targetVersion: null, targetColumn: null },
      };
    }

    default:
      return state;
  }
}

export { initialDatasetState };
