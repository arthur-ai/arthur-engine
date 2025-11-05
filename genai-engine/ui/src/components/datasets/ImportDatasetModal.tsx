import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import React, { useCallback, useState } from "react";

import {
  CSV_IMPORT_MESSAGES,
  DEFAULT_CONFIG,
  type CsvParseConfig,
  type ParsedPreviewData,
  type ValidationResult,
} from "./import/csvImportConstants";
import {
  autoDetectDelimiter,
  parseCSVFull,
  parseCSVPreview,
} from "./import/csvParseUtils";
import { ImportConfigurationStep } from "./import/ImportConfigurationStep";
import { ImportPreviewStep } from "./import/ImportPreviewStep";

interface ImportDatasetModalProps {
  open: boolean;
  onClose: () => void;
  onImport: (columns: string[], rows: Record<string, string>[]) => void;
  currentRowCount: number;
}

type AutoDetectStatus = "idle" | "detecting" | "detected";
type ProcessingStatus = "idle" | "processing" | "error";

interface PreviewState {
  data: ParsedPreviewData;
  validation: ValidationResult;
}

export const ImportDatasetModal: React.FC<ImportDatasetModalProps> = ({
  open,
  onClose,
  onImport,
  currentRowCount,
}) => {
  const [step, setStep] = useState<0 | 1>(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [config, setConfig] = useState<CsvParseConfig>(DEFAULT_CONFIG);

  const [autoDetectStatus, setAutoDetectStatus] =
    useState<AutoDetectStatus>("idle");
  const [processingStatus, setProcessingStatus] =
    useState<ProcessingStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [previewState, setPreviewState] = useState<PreviewState | null>(null);

  const resetState = useCallback(() => {
    setStep(0);
    setSelectedFile(null);
    setConfig(DEFAULT_CONFIG);
    setAutoDetectStatus("idle");
    setProcessingStatus("idle");
    setErrorMessage(null);
    setPreviewState(null);
  }, []);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      setSelectedFile(file);
      setErrorMessage(null);
      setAutoDetectStatus("detecting");

      try {
        const detectedDelimiter = await autoDetectDelimiter(file);
        setConfig((prev) => ({ ...prev, delimiter: detectedDelimiter }));
        setAutoDetectStatus("detected");
      } catch {
        setErrorMessage(CSV_IMPORT_MESSAGES.errors.autoDetectFailed);
        setAutoDetectStatus("idle");
      }
    },
    []
  );

  const handleNext = useCallback(() => {
    if (!selectedFile) return;

    setProcessingStatus("processing");
    setErrorMessage(null);

    parseCSVPreview(
      selectedFile,
      config,
      currentRowCount,
      (data, validation) => {
        setProcessingStatus("idle");
        setPreviewState({ data, validation });

        if (validation.isValid) {
          setStep(1);
        } else {
          setProcessingStatus("error");
          setErrorMessage(validation.errors.join("; "));
        }
      },
      (error) => {
        setProcessingStatus("error");
        setErrorMessage(error);
      }
    );
  }, [selectedFile, config, currentRowCount]);

  const handleFinalImport = useCallback(() => {
    if (!selectedFile) return;

    setProcessingStatus("processing");
    setErrorMessage(null);

    parseCSVFull(
      selectedFile,
      config,
      currentRowCount,
      (columns, rows) => {
        setProcessingStatus("idle");
        onImport(columns, rows);
        resetState();
        onClose();
      },
      (error) => {
        setProcessingStatus("error");
        setErrorMessage(error);
      }
    );
  }, [selectedFile, config, currentRowCount, onImport, onClose, resetState]);

  const handleClose = useCallback(() => {
    if (processingStatus !== "processing") {
      resetState();
      onClose();
    }
  }, [processingStatus, resetState, onClose]);

  const handleBack = useCallback(() => {
    setStep(0);
    setPreviewState(null);
    setErrorMessage(null);
    setProcessingStatus("idle");
  }, []);

  const isAutoDetecting = autoDetectStatus === "detecting";
  const isAutoDetected = autoDetectStatus === "detected";
  const isProcessing = processingStatus === "processing";
  const isDisabled = isProcessing || isAutoDetecting;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {step === 0
          ? CSV_IMPORT_MESSAGES.labels.configureTitle
          : CSV_IMPORT_MESSAGES.labels.previewTitle}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, py: 1 }}>
          {step === 0 ? (
            <ImportConfigurationStep
              selectedFile={selectedFile}
              config={config}
              isAutoDetecting={isAutoDetecting}
              autoDetected={isAutoDetected}
              error={errorMessage}
              onFileChange={handleFileChange}
              onConfigChange={setConfig}
            />
          ) : previewState ? (
            <ImportPreviewStep
              previewData={previewState.data}
              validation={previewState.validation}
              currentRowCount={currentRowCount}
              error={errorMessage}
            />
          ) : null}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        {step === 0 ? (
          <>
            <Button
              onClick={handleClose}
              color="inherit"
              disabled={isProcessing}
            >
              {CSV_IMPORT_MESSAGES.labels.cancel}
            </Button>
            <Button
              onClick={handleNext}
              variant="contained"
              disabled={!selectedFile || isDisabled}
            >
              {isProcessing
                ? CSV_IMPORT_MESSAGES.info.processing
                : CSV_IMPORT_MESSAGES.labels.next}
            </Button>
          </>
        ) : (
          <>
            <Button
              onClick={handleBack}
              color="inherit"
              disabled={isProcessing}
            >
              {CSV_IMPORT_MESSAGES.labels.back}
            </Button>
            <Button
              onClick={handleClose}
              color="inherit"
              disabled={isProcessing}
            >
              {CSV_IMPORT_MESSAGES.labels.cancel}
            </Button>
            <Button
              onClick={handleFinalImport}
              variant="contained"
              color="primary"
              disabled={
                isProcessing ||
                !previewState?.validation.isValid ||
                previewState.data.totalRows === 0
              }
            >
              {isProcessing
                ? CSV_IMPORT_MESSAGES.info.importing
                : CSV_IMPORT_MESSAGES.labels.import}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};
