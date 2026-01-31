import { ArrowBack, Check } from "@mui/icons-material";
import { Box, Button, Divider, Alert } from "@mui/material";
import React, { useCallback, useMemo, useState } from "react";

import { SyntheticDataChat } from "./SyntheticDataChat";
import { SyntheticDataTable } from "./SyntheticDataTable";
import type { SyntheticRow } from "./types";

import type { OpenAIMessageInput } from "@/lib/api-client/api-client";

interface SyntheticDataCanvasProps {
  rows: SyntheticRow[];
  conversation: OpenAIMessageInput[];
  columns: string[];
  isLoading: boolean;
  error: Error | null;
  onSendMessage: (message: string) => void;
  onUpdateRow: (id: string, data: Record<string, string>) => void;
  onAddRow: (data: Record<string, string>) => void;
  onDeleteRows: (ids: string[]) => void;
  onToggleLock: (id: string) => void;
  onBack: () => void;
  onAccept: (selectedIds: Set<string>) => void;
}

export const SyntheticDataCanvas: React.FC<SyntheticDataCanvasProps> = ({
  rows,
  conversation,
  columns,
  isLoading,
  error,
  onSendMessage,
  onUpdateRow,
  onAddRow,
  onDeleteRows,
  onToggleLock,
  onBack,
  onAccept,
}) => {
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());

  // Locked rows are always treated as selected. The effective selection is
  // the user's checkbox selection merged with all locked row IDs.
  // When nothing is explicitly selected (no checkboxes checked), accept all rows.
  const lockedIds = useMemo(
    () => new Set(rows.filter((r) => r.locked).map((r) => r.id)),
    [rows]
  );

  // What the table shows as "checked": user selections + locked rows
  const visibleSelection = useMemo(() => {
    const merged = new Set(selectedRows);
    for (const id of lockedIds) {
      merged.add(id);
    }
    return merged;
  }, [selectedRows, lockedIds]);

  // What gets accepted: if any rows are selected (user checkboxes OR locked rows),
  // use that selection. Otherwise accept all rows.
  const effectiveSelection = useMemo(() => {
    if (visibleSelection.size > 0) {
      return visibleSelection;
    }
    return new Set(rows.map((r) => r.id));
  }, [rows, visibleSelection]);

  const handleAccept = useCallback(() => {
    onAccept(effectiveSelection);
  }, [onAccept, effectiveSelection]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Main content area - split view */}
      <Box
        sx={{
          display: "flex",
          flex: 1,
          overflow: "hidden",
        }}
      >
        {/* Left panel - Chat */}
        <Box
          sx={{
            width: "40%",
            minWidth: 300,
            maxWidth: 500,
            display: "flex",
            flexDirection: "column",
            borderRight: 1,
            borderColor: "divider",
          }}
        >
          <SyntheticDataChat
            conversation={conversation}
            isLoading={isLoading}
            onSendMessage={onSendMessage}
          />
        </Box>

        {/* Right panel - Table */}
        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {error && (
            <Alert severity="error" sx={{ m: 2 }}>
              {error.message}
            </Alert>
          )}
          <SyntheticDataTable
            rows={rows}
            columns={columns}
            selectedRows={visibleSelection}
            onSelectedRowsChange={setSelectedRows}
            onUpdateRow={onUpdateRow}
            onAddRow={onAddRow}
            onDeleteRows={onDeleteRows}
            onToggleLock={onToggleLock}
          />
        </Box>
      </Box>

      {/* Footer with actions */}
      <Divider />
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          p: 2,
          bgcolor: "grey.50",
        }}
      >
        <Button
          startIcon={<ArrowBack />}
          onClick={onBack}
          disabled={isLoading}
          variant="outlined"
        >
          Back to Configure
        </Button>
        <Button
          variant="contained"
          color="primary"
          startIcon={<Check />}
          onClick={handleAccept}
          disabled={rows.length === 0 || isLoading}
        >
          Accept {effectiveSelection.size} Row{effectiveSelection.size !== 1 ? "s" : ""}
        </Button>
      </Box>
    </Box>
  );
};
