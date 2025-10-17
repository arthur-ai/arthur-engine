import { useCallback, useEffect, useMemo, useState } from "react";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";
import { Dataset } from "@/types/dataset";
import { generateTempRowId } from "@/utils/datasetRowUtils";
import { getColumnNames } from "@/utils/datasetUtils";

export interface PendingChanges {
  added: DatasetVersionRowResponse[];
  updated: DatasetVersionRowResponse[];
  deleted: string[];
}

export interface UseDatasetLocalStateReturn {
  localColumns: string[];
  localRows: DatasetVersionRowResponse[];
  pendingChanges: PendingChanges;
  hasUnsavedChanges: boolean;

  addColumn: (name: string) => void;
  addRow: (rowData: Record<string, unknown>) => void;
  updateRow: (id: string, rowData: Record<string, unknown>) => void;
  deleteRow: (id: string) => void;
  clearChanges: () => void;
}

export function useDatasetLocalState(
  dataset: Dataset | undefined,
  versionRows: DatasetVersionRowResponse[] | undefined
): UseDatasetLocalStateReturn {
  const [localColumns, setLocalColumns] = useState<string[]>([]);
  const [localRows, setLocalRows] = useState<DatasetVersionRowResponse[]>([]);
  const [pendingChanges, setPendingChanges] = useState<PendingChanges>({
    added: [],
    updated: [],
    deleted: [],
  });

  useEffect(() => {
    if (dataset) {
      const metadataColumns = getColumnNames(dataset.metadata);
      setLocalColumns(metadataColumns);
    }
  }, [dataset]);

  useEffect(() => {
    if (versionRows) {
      setLocalRows(versionRows);
      setPendingChanges({ added: [], updated: [], deleted: [] });
    }
  }, [versionRows]);

  const hasUnsavedChanges = useMemo(() => {
    return (
      pendingChanges.added.length > 0 ||
      pendingChanges.updated.length > 0 ||
      pendingChanges.deleted.length > 0
    );
  }, [pendingChanges]);

  const addColumn = useCallback((name: string) => {
    setLocalColumns((prev) => [...prev, name]);
  }, []);

  const addRow = useCallback((rowData: Record<string, unknown>) => {
    const newRow: DatasetVersionRowResponse = {
      id: generateTempRowId(),
      data: Object.entries(rowData).map(([column_name, column_value]) => ({
        column_name,
        column_value: String(column_value),
      })),
    };

    setLocalRows((prev) => [...prev, newRow]);
    setPendingChanges((prev) => ({
      ...prev,
      added: [...prev.added, newRow],
    }));
  }, []);

  const updateRow = useCallback(
    (id: string, rowData: Record<string, unknown>) => {
      const updatedRow: DatasetVersionRowResponse = {
        id,
        data: Object.entries(rowData).map(([column_name, column_value]) => ({
          column_name,
          column_value: String(column_value),
        })),
      };

      setLocalRows((prev) =>
        prev.map((row) => (row.id === id ? updatedRow : row))
      );

      const isNewRow = pendingChanges.added.some((r) => r.id === id);
      if (isNewRow) {
        setPendingChanges((prev) => ({
          ...prev,
          added: prev.added.map((r) => (r.id === id ? updatedRow : r)),
        }));
      } else {
        setPendingChanges((prev) => {
          const alreadyTracked = prev.updated.some((r) => r.id === id);
          return {
            ...prev,
            updated: alreadyTracked
              ? prev.updated.map((r) => (r.id === id ? updatedRow : r))
              : [...prev.updated, updatedRow],
          };
        });
      }
    },
    [pendingChanges.added]
  );

  const deleteRow = useCallback(
    (id: string) => {
      setLocalRows((prev) => prev.filter((row) => row.id !== id));

      const isNewRow = pendingChanges.added.some((r) => r.id === id);
      if (isNewRow) {
        setPendingChanges((prev) => ({
          ...prev,
          added: prev.added.filter((r) => r.id !== id),
        }));
      } else {
        setPendingChanges((prev) => ({
          ...prev,
          deleted: [...prev.deleted, id],
          updated: prev.updated.filter((r) => r.id !== id),
        }));
      }
    },
    [pendingChanges.added]
  );

  const clearChanges = useCallback(() => {
    setPendingChanges({ added: [], updated: [], deleted: [] });
  }, []);

  return {
    localColumns,
    localRows,
    pendingChanges,
    hasUnsavedChanges,
    addColumn,
    addRow,
    updateRow,
    deleteRow,
    clearChanges,
  };
}
