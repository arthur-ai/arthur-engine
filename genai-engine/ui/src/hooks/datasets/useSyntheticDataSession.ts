import { useCallback, useState } from "react";

import type { GenerationConfig, SyntheticRow } from "@/components/datasets/synthetic/types";
import { useApi } from "@/hooks/useApi";
import type {
  OpenAIMessageInput,
  SyntheticDataRowResponse,
  NewDatasetVersionRowColumnItemRequest,
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
  startGeneration: (config: GenerationConfig) => Promise<void>;

  // Conversation
  sendMessage: (message: string, config: GenerationConfig) => Promise<void>;

  // Manual edits
  updateRow: (id: string, data: Record<string, string>) => void;
  addRow: (data: Record<string, string>) => void;
  deleteRows: (ids: string[]) => void;

  // Session management
  reset: () => void;
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
      const existing = existingRowMap.get(apiRow.id);
      if (existing) {
        status = existing.status;
      }
    }

    return {
      id: apiRow.id,
      data,
      status,
    };
  });
}

function syntheticRowsToApiFormat(
  rows: SyntheticRow[]
): { data: NewDatasetVersionRowColumnItemRequest[] }[] {
  return rows.map((row) => ({
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
    async (config: GenerationConfig) => {
      if (!api) {
        setError(new Error("API client not available"));
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
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

        const response =
          await api.api.sendSyntheticDataMessageApiV2DatasetsDatasetIdVersionsVersionNumberGenerateSyntheticMessagePost(
            datasetId,
            versionNumber,
            {
              message,
              current_rows: syntheticRowsToApiFormat(rows),
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

        const newRows = apiRowsToSyntheticRows(
          response.data.rows,
          response.data.rows_added ?? [],
          response.data.rows_modified ?? [],
          rows
        );
        setRows(newRows);

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
    reset,
  };
}
