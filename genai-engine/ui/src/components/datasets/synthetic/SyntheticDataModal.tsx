import { AutoAwesome, Close } from "@mui/icons-material";
import {
  Box,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from "@mui/material";
import React, { useCallback, useState } from "react";

import { SyntheticDataCanvas } from "./SyntheticDataCanvas";
import { SyntheticDataConfigForm } from "./SyntheticDataConfigForm";
import type { GenerationConfig } from "./types";

import { useSyntheticDataSession } from "@/hooks/datasets/useSyntheticDataSession";
import type { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

interface SyntheticDataModalProps {
  open: boolean;
  onClose: () => void;
  columns: string[];
  existingRowsSample: DatasetVersionRowResponse[];
  datasetId: string;
  versionNumber: number;
  onAcceptRows: (rows: { data: { column_name: string; column_value: string }[] }[]) => void;
}

type ModalPhase = "configure" | "canvas";

export const SyntheticDataModal: React.FC<SyntheticDataModalProps> = ({
  open,
  onClose,
  columns,
  existingRowsSample,
  datasetId,
  versionNumber,
  onAcceptRows,
}) => {
  const [phase, setPhase] = useState<ModalPhase>("configure");
  const [config, setConfig] = useState<GenerationConfig | null>(null);

  const session = useSyntheticDataSession(datasetId, versionNumber, columns);

  const handleStartGeneration = useCallback(
    async (generationConfig: GenerationConfig) => {
      setConfig(generationConfig);
      await session.startGeneration(generationConfig, existingRowsSample);
      setPhase("canvas");
    },
    [session, existingRowsSample]
  );

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (config) {
        await session.sendMessage(message, config);
      }
    },
    [session, config]
  );

  const handleClose = useCallback(() => {
    setPhase("configure");
    setConfig(null);
    session.reset();
    onClose();
  }, [session, onClose]);

  const handleAcceptRows = useCallback(() => {
    // Convert synthetic rows to the format expected by the dataset
    const rowsToAdd = session.rows.map((row) => ({
      data: Object.entries(row.data).map(([column_name, column_value]) => ({
        column_name,
        column_value,
      })),
    }));
    onAcceptRows(rowsToAdd);
    handleClose();
  }, [session.rows, onAcceptRows, handleClose]);

  const handleBack = useCallback(() => {
    setPhase("configure");
    session.reset();
  }, [session]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth={phase === "canvas" ? "xl" : "md"}
      fullWidth
      PaperProps={{
        sx: {
          height: phase === "canvas" ? "90vh" : "auto",
          maxHeight: phase === "canvas" ? "90vh" : "auto",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pb: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <AutoAwesome color="primary" />
          <Typography variant="h6">
            {phase === "configure"
              ? "Generate Synthetic Data"
              : "Synthetic Data Generation"}
          </Typography>
        </Box>
        <IconButton onClick={handleClose} size="small">
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent
        sx={{
          display: "flex",
          flexDirection: "column",
          height: phase === "canvas" ? "calc(100% - 64px)" : "auto",
          p: phase === "canvas" ? 0 : 3,
        }}
      >
        {phase === "configure" ? (
          <SyntheticDataConfigForm
            columns={columns}
            existingRowsSample={existingRowsSample}
            onSubmit={handleStartGeneration}
            onCancel={handleClose}
            isLoading={session.isLoading}
          />
        ) : (
          <SyntheticDataCanvas
            rows={session.rows}
            conversation={session.conversation}
            columns={columns}
            isLoading={session.isLoading}
            error={session.error}
            onSendMessage={handleSendMessage}
            onUpdateRow={session.updateRow}
            onAddRow={session.addRow}
            onDeleteRows={session.deleteRows}
            onToggleLock={session.toggleLock}
            onBack={handleBack}
            onAccept={handleAcceptRows}
          />
        )}
      </DialogContent>
    </Dialog>
  );
};
