import { useCallback, useState } from "react";

import type { GenerationConfig, SyntheticRow } from "@/components/datasets/synthetic/types";
import { useApi } from "@/hooks/useApi";
import type {
  OpenAIMessageInput,
  SyntheticDataRowResponse,
  NewDatasetVersionRowColumnItemRequest,
  DatasetVersionRowResponse,
} from "@/lib/api-client/api-client";
import { generateTempRowId } from "@/utils/datasetRowUtils";

export type { GenerationConfig, SyntheticRow };

export interface UseSyntheticDataSessionReturn {
  // State
  rows: SyntheticRow[];
  conversation: OpenAIMessageInput[];
  isLoading: boolean;
  error: Error | null;

  // Initial generation
  startGeneration: (config: GenerationConfig, existingRowsSample?: DatasetVersionRowResponse[]) => Promise<void>;

  // Conversation
  sendMessage: (message: string, config: GenerationConfig) => Promise<void>;

  // Manual edits
  updateRow: (id: string, data: Record<string, string>) => void;
  addRow: (data: Record<string, string>) => void;
  deleteRows: (ids: string[]) => void;
  toggleLock: (id: string) => void;

  // Session management
  reset: () => void;
}

function datasetVersionRowsToSyntheticRows(
  datasetRows: DatasetVersionRowResponse[]
): SyntheticRow[] {
  return datasetRows.map((datasetRow) => {
    const data: Record<string, string> = {};
    datasetRow.data.forEach((col) => {
      data[col.column_name] = col.column_value;
    });

    return {
      id: datasetRow.id,
      data,
      status: "generated" as const,
    };
  });
}

function apiRowsToSyntheticRows(
  apiRows: SyntheticDataRowResponse[],
  rowsAdded: string[],
  rowsModified: string[],
  existingRows: SyntheticRow[]
): SyntheticRow[] {
  const rowsAddedSet = new Set(rowsAdded);
  const rowsModifiedSet = new Set(rowsModified);
  const existingRowMap = new Map(existingRows.map((r) => [r.id, r]));

  return apiRows.map((apiRow) => {
    // If this row exists and is locked, keep it unchanged
    const existingRow = existingRowMap.get(apiRow.id);
    if (existingRow?.locked) {
      return existingRow;
    }

    const data: Record<string, string> = {};
    apiRow.data.forEach((col) => {
      data[col.column_name] = col.column_value;
    });

    let status: SyntheticRow["status"] = "generated";
    if (rowsAddedSet.has(apiRow.id)) {
      status = "generated";
    } else if (rowsModifiedSet.has(apiRow.id)) {
      status = "modified";
    } else {
      // Keep existing status if row wasn't changed
      if (existingRow) {
        status = existingRow.status;
      }
    }

    return {
      id: apiRow.id,
      data,
      status,
      locked: existingRow?.locked,
    };
  });
}

function syntheticRowsToApiFormat(
  rows: SyntheticRow[]
): { id?: string; data: NewDatasetVersionRowColumnItemRequest[] }[] {
  return rows.map((row) => ({
    id: row.id,
    data: Object.entries(row.data).map(([column_name, column_value]) => ({
      column_name,
      column_value,
    })),
  }));
}

export function useSyntheticDataSession(
  datasetId: string,
  versionNumber: number,
  _columns: string[]
): UseSyntheticDataSessionReturn {
  const api = useApi();

  const [rows, setRows] = useState<SyntheticRow[]>([]);
  const [conversation, setConversation] = useState<OpenAIMessageInput[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const startGeneration = useCallback(
    async (config: GenerationConfig, existingRowsSample?: DatasetVersionRowResponse[]) => {
      if (!api) {
        setError(new Error("API client not available"));
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // If editExisting is enabled and we have existing rows, load them into the canvas first
        if (config.editExisting && existingRowsSample && existingRowsSample.length > 0) {
          const existingRows = datasetVersionRowsToSyntheticRows(existingRowsSample);
          setRows(existingRows);

          // Initialize conversation without calling the API - just show the existing data
          setConversation([
            {
              role: "assistant",
              content: `I've loaded ${existingRows.length} existing row${existingRows.length !== 1 ? 's' : ''} from your dataset. You can now edit them directly in the table, or ask me to modify or generate additional data.`,
            },
          ]);
        } else {
          // Generate new data
          const response =
            await api.api.generateSyntheticDataApiV2DatasetsDatasetIdVersionsVersionNumberGenerateSyntheticPost(
              datasetId,
              versionNumber,
              {
                dataset_purpose: config.datasetPurpose,
                column_descriptions: config.columnDescriptions.map((col) => ({
                  column_name: col.columnName,
                  description: col.description,
                })),
                num_rows: config.numRows,
                model_provider: config.modelProvider,
                model_name: config.modelName,
                config: config.temperature
                  ? { temperature: config.temperature }
                  : undefined,
              }
            );

          const newRows = apiRowsToSyntheticRows(
            response.data.rows,
            response.data.rows_added ?? [],
            response.data.rows_modified ?? [],
            []
          );
          setRows(newRows);

          // Initialize conversation with the assistant's response
          setConversation([
            {
              role: "assistant",
              content: response.data.assistant_message.content as string,
            },
          ]);
        }
      } catch (err) {
        console.error("Failed to generate synthetic data:", err);
        setError(err as Error);
      } finally {
        setIsLoading(false);
      }
    },
    [api, datasetId, versionNumber]
  );

  const sendMessage = useCallback(
    async (message: string, config: GenerationConfig) => {
      if (!api) {
        setError(new Error("API client not available"));
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        // Add user message to conversation first
        const userMessage: OpenAIMessageInput = {
          role: "user",
          content: message,
        };
        const updatedConversation = [...conversation, userMessage];

        // Filter out locked rows before sending to the backend
        const unlockedRows = rows.filter((row) => !row.locked);

        const response =
          await api.api.sendSyntheticDataMessageApiV2DatasetsDatasetIdVersionsVersionNumberGenerateSyntheticMessagePost(
            datasetId,
            versionNumber,
            {
              message,
              current_rows: syntheticRowsToApiFormat(unlockedRows),
              conversation_history: updatedConversation,
              dataset_purpose: config.datasetPurpose,
              column_descriptions: config.columnDescriptions.map((col) => ({
                column_name: col.columnName,
                description: col.description,
              })),
              model_provider: config.modelProvider,
              model_name: config.modelName,
              config: config.temperature
                ? { temperature: config.temperature }
                : undefined,
            }
          );

        // Only pass unlocked rows as existing rows context (locked rows are handled separately)
        const unlockedRowsContext = rows.filter((r) => !r.locked);

        const newUnlockedRows = apiRowsToSyntheticRows(
          response.data.rows,
          response.data.rows_added ?? [],
          response.data.rows_modified ?? [],
          unlockedRowsContext
        );

        // Merge locked rows back in at their original positions
        const newRowsMap = new Map(newUnlockedRows.map((r) => [r.id, r]));
        const mergedRows = rows.map((row) => {
          // Keep locked rows as-is with their locked state preserved
          if (row.locked) {
            return row;
          }
          // Replace unlocked rows with the updated version from the backend
          return newRowsMap.get(row.id) || row;
        });

        // Add any new rows that weren't in the original set (newly generated rows)
        const existingIds = new Set(rows.map((r) => r.id));
        const additionalNewRows = newUnlockedRows.filter((r) => !existingIds.has(r.id));

        setRows([...mergedRows, ...additionalNewRows]);

        // Add assistant response to conversation
        setConversation([
          ...updatedConversation,
          {
            role: "assistant",
            content: response.data.assistant_message.content as string,
          },
        ]);
      } catch (err) {
        console.error("Failed to send message:", err);
        setError(err as Error);
      } finally {
        setIsLoading(false);
      }
    },
    [api, datasetId, versionNumber, rows, conversation]
  );

  const updateRow = useCallback(
    (id: string, data: Record<string, string>) => {
      setRows((prevRows) =>
        prevRows.map((row) =>
          row.id === id
            ? { ...row, data, status: "modified" as const }
            : row
        )
      );
    },
    []
  );

  const addRow = useCallback(
    (data: Record<string, string>) => {
      const newRow: SyntheticRow = {
        id: generateTempRowId(),
        data,
        status: "added",
      };
      setRows((prevRows) => [...prevRows, newRow]);
    },
    []
  );

  const deleteRows = useCallback((ids: string[]) => {
    const idsSet = new Set(ids);
    setRows((prevRows) => prevRows.filter((row) => !idsSet.has(row.id)));
  }, []);

  const toggleLock = useCallback((id: string) => {
    setRows((prevRows) =>
      prevRows.map((row) =>
        row.id === id ? { ...row, locked: !row.locked } : row
      )
    );
  }, []);

  const reset = useCallback(() => {
    setRows([]);
    setConversation([]);
    setError(null);
  }, []);

  return {
    rows,
    conversation,
    isLoading,
    error,
    startGeneration,
    sendMessage,
    updateRow,
    addRow,
    deleteRows,
    toggleLock,
    reset,
  };
}
