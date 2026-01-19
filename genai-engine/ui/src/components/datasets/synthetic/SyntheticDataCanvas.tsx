import { ArrowBack, Check } from "@mui/icons-material";
import { Box, Button, Divider, Alert } from "@mui/material";
import React from "react";

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
  onAccept: () => void;
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
          onClick={onAccept}
          disabled={rows.length === 0 || isLoading}
        >
          Accept {rows.length} Row{rows.length !== 1 ? "s" : ""}
        </Button>
      </Box>
    </Box>
  );
};
