import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import {
  Box,
  Typography,
  Chip,
  Card,
  CardContent,
  Modal,
  IconButton,
  CircularProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
} from "@mui/material";
import React, { useEffect, useState } from "react";

import { getRagConfigDisplayName, type RagConfig } from "./utils";

import { ResultsDisplay } from "@/components/retrievals/ResultsDisplay";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { RagTestCase, EvalExecution } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

interface RagTestCaseDetailModalProps {
  testCase: RagTestCase | null;
  open: boolean;
  onClose: () => void;
  currentIndex: number;
  totalCount: number;
  onPrevious: () => void;
  onNext: () => void;
  ragConfigs: RagConfig[];
  datasetId: string;
  datasetVersion: number;
}

interface DatasetRowSectionProps {
  datasetId: string;
  versionNumber: number;
  rowId: string;
}

const DatasetRowSection: React.FC<DatasetRowSectionProps> = ({ datasetId, versionNumber, rowId }) => {
  const {
    data: rowData,
    isPending,
    error,
  } = useApiQuery({
    method: "getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet",
    args: [datasetId, versionNumber, rowId],
  });

  if (isPending) {
    return (
      <Box className="flex justify-center items-center py-4">
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded">
        <Typography color="error" variant="body2">
          {error.message}
        </Typography>
      </Box>
    );
  }

  if (!rowData) return null;

  return (
    <Box className="space-y-3">
      {rowData.data.map((item, index) => (
        <Box key={index} className="p-3 bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
          <Typography variant="subtitle2" className="font-semibold text-gray-700 dark:text-gray-300 mb-1">
            {item.column_name}
          </Typography>
          <Typography variant="body2" className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap wrap-break-word">
            {item.column_value}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

interface EvalInputsDialogProps {
  open: boolean;
  onClose: () => void;
  evalExecution: EvalExecution | null;
}

const EvalInputsDialog: React.FC<EvalInputsDialogProps> = ({ open, onClose, evalExecution }) => {
  if (!evalExecution) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Eval Inputs: {evalExecution.eval_name} v{evalExecution.eval_version}
      </DialogTitle>
      <DialogContent>
        <Stack gap={2} className="mt-2">
          {evalExecution.eval_input_variables.map((variable, index) => (
            <Box key={index} className="p-3 bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
              <Typography variant="subtitle2" className="font-semibold text-gray-700 dark:text-gray-300 mb-1">
                {variable.variable_name}
              </Typography>
              <Typography variant="body2" className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap wrap-break-word font-mono text-sm">
                {variable.value}
              </Typography>
            </Box>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

const getEvalChipSx = (isPass: boolean) => {
  const color = isPass ? "success.main" : "error.main";
  return {
    backgroundColor: "transparent",
    color: color,
    borderColor: color,
    borderWidth: 1,
    borderStyle: "solid",
  };
};

const getPendingChipSx = () => ({
  backgroundColor: "transparent",
  color: "text.secondary",
  borderColor: "text.secondary",
  borderWidth: 1,
  borderStyle: "solid",
});

// Infer search method from RAG output metadata
// Note: RagSearchOutput.response is RagProviderQueryResponse, which contains response: WeaviateQueryResults
const inferSearchMethod = (output: RagTestCase["rag_results"][0]["output"]): "nearText" | "bm25" | "hybrid" => {
  if (!output?.response?.response?.objects?.[0]?.metadata) return "nearText";
  const metadata = output.response.response.objects[0].metadata;

  // If we have both score and distance, it's likely hybrid
  if (metadata.score !== undefined && metadata.distance !== undefined) {
    return "hybrid";
  }
  // If we only have score, it's BM25
  if (metadata.score !== undefined && metadata.distance === undefined) {
    return "bm25";
  }
  // Default to nearText (vector similarity)
  return "nearText";
};

export const RagTestCaseDetailModal: React.FC<RagTestCaseDetailModalProps> = ({
  testCase,
  open,
  onClose,
  currentIndex,
  totalCount,
  onPrevious,
  onNext,
  ragConfigs,
  datasetId,
  datasetVersion,
}) => {
  const [evalInputsDialogOpen, setEvalInputsDialogOpen] = useState(false);
  const [selectedEvalExecution, setSelectedEvalExecution] = useState<EvalExecution | null>(null);

  // Add keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!open || evalInputsDialogOpen) return;

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        onPrevious();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        onNext();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, evalInputsDialogOpen, onPrevious, onNext]);

  const handleViewEvalInputs = (evalExecution: EvalExecution) => {
    setSelectedEvalExecution(evalExecution);
    setEvalInputsDialogOpen(true);
  };

  const handleCloseEvalInputsDialog = () => {
    setEvalInputsDialogOpen(false);
    setSelectedEvalExecution(null);
  };

  if (!testCase) return null;

  return (
    <>
      <Modal open={open} onClose={onClose} aria-labelledby="rag-test-case-detail-modal">
        <Box className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[95vw] max-w-7xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-lg shadow-xl overflow-auto">
          {/* Modal Header */}
          <Box className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center z-10">
            <Box className="flex items-center gap-3">
              <IconButton onClick={onPrevious} size="small" disabled={currentIndex <= 0} className="hover:bg-gray-100 dark:hover:bg-gray-800">
                <ArrowBackIcon />
              </IconButton>
              <Typography variant="h6" className="font-semibold text-gray-900 dark:text-gray-100">
                Test Case {currentIndex + 1} of {totalCount}
              </Typography>
              <IconButton
                onClick={onNext}
                size="small"
                disabled={currentIndex >= totalCount - 1}
                className="hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                <ArrowForwardIcon />
              </IconButton>
              <Chip
                label={testCase.status.charAt(0).toUpperCase() + testCase.status.slice(1)}
                size="small"
                color={testCase.status === "completed" ? "success" : testCase.status === "failed" ? "error" : "default"}
              />
              {testCase.total_cost && <Chip label={`Cost: ${formatCurrency(parseFloat(testCase.total_cost))}`} size="small" variant="outlined" />}
            </Box>
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Modal Content */}
          <Box className="p-6">
            {/* Dataset Row Section */}
            <Box className="mb-6">
              <Typography
                variant="h6"
                className="font-bold mb-4 pb-2 border-b-2 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100"
              >
                Dataset Row
              </Typography>
              <DatasetRowSection datasetId={datasetId} versionNumber={datasetVersion} rowId={testCase.dataset_row_id} />
            </Box>

            {/* RAG Results Section */}
            <Box>
              <Typography
                variant="h6"
                className="font-bold mb-4 pb-2 border-b-2 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100"
              >
                RAG Results
              </Typography>
              <Box className="space-y-6">
                {testCase.rag_results.map((ragResult, index) => {
                  // Find the matching config for display name
                  const displayName = getRagConfigDisplayName(
                    {
                      rag_config_key: ragResult.rag_config_key,
                      rag_config_type: ragResult.rag_config_type,
                      setting_configuration_id: ragResult.setting_configuration_id || undefined,
                      setting_configuration_version: ragResult.setting_configuration_version || undefined,
                      eval_results: [],
                    },
                    ragConfigs
                  );

                  const searchMethod = inferSearchMethod(ragResult.output);

                  return (
                    <Card key={ragResult.rag_config_key || index} elevation={2}>
                      {/* RAG Config Header */}
                      <Box className="bg-blue-100 dark:bg-blue-900/40 border-b border-blue-200 dark:border-blue-800 px-4 py-3 flex items-center justify-between">
                        <Box className="flex items-center gap-2">
                          <Typography variant="h6" className="font-semibold text-blue-900 dark:text-blue-200">
                            {displayName}
                          </Typography>
                          {ragResult.rag_config_type === "unsaved" && (
                            <Chip
                              label="Unsaved"
                              size="small"
                              sx={{
                                backgroundColor: (theme) => (theme.palette.mode === "dark" ? "rgba(255,152,0,0.12)" : "#fff3e0"),
                                color: (theme) => (theme.palette.mode === "dark" ? "#ffb74d" : "#f57c00"),
                                fontWeight: 600,
                              }}
                            />
                          )}
                        </Box>
                      </Box>

                      <CardContent>
                        {/* Query Text */}
                        <Box className="mb-4">
                          <Typography variant="subtitle2" className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Query Text:
                          </Typography>
                          <Box className="p-3 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded">
                            <Typography variant="body2" className="whitespace-pre-wrap text-gray-900 dark:text-gray-100">
                              {ragResult.query_text}
                            </Typography>
                          </Box>
                        </Box>

                        {/* RAG Search Results */}
                        <Box className="mb-4">
                          <Typography variant="subtitle2" className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Retrieved Documents:
                          </Typography>
                          {ragResult.output?.response?.response ? (
                            <ResultsDisplay
                              results={ragResult.output.response.response}
                              isLoading={false}
                              error={null}
                              query={ragResult.query_text}
                              searchMethod={searchMethod}
                            />
                          ) : (
                            <Box className="p-3 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded">
                              <Typography variant="body2" className="text-gray-500 dark:text-gray-400 italic">
                                No results available yet
                              </Typography>
                            </Box>
                          )}
                        </Box>

                        {/* Evaluations */}
                        {ragResult.evals.length > 0 && (
                          <Box>
                            <Typography variant="subtitle2" className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                              Evaluations:
                            </Typography>
                            <Box className="space-y-2">
                              {ragResult.evals.map((evalItem, evalIndex) => (
                                <Box
                                  key={evalIndex}
                                  className="p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded"
                                >
                                  <Box className="flex items-center justify-between mb-2">
                                    <Box className="flex items-center gap-2">
                                      <Typography variant="body2" className="font-medium text-gray-900 dark:text-gray-100">
                                        {evalItem.eval_name} v{evalItem.eval_version}
                                      </Typography>
                                      {evalItem.eval_results ? (
                                        <>
                                          <Chip
                                            label={evalItem.eval_results.score === 1 ? "Pass" : "Fail"}
                                            size="small"
                                            sx={getEvalChipSx(evalItem.eval_results.score === 1)}
                                          />
                                          <Chip
                                            label={`Cost: ${formatCurrency(parseFloat(evalItem.eval_results.cost))}`}
                                            size="small"
                                            variant="outlined"
                                          />
                                        </>
                                      ) : (
                                        <Chip label="Pending" size="small" sx={getPendingChipSx()} />
                                      )}
                                    </Box>
                                    <Button
                                      size="small"
                                      variant="outlined"
                                      startIcon={<InfoOutlinedIcon />}
                                      onClick={() => handleViewEvalInputs(evalItem)}
                                    >
                                      View Inputs
                                    </Button>
                                  </Box>
                                  {evalItem.eval_results?.explanation && (
                                    <Typography variant="body2" className="text-gray-700 dark:text-gray-300 mt-1">
                                      {evalItem.eval_results.explanation}
                                    </Typography>
                                  )}
                                </Box>
                              ))}
                            </Box>
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </Box>
            </Box>
          </Box>
        </Box>
      </Modal>

      {/* Eval Inputs Dialog - rendered as sibling to avoid nesting in Modal */}
      <EvalInputsDialog open={evalInputsDialogOpen} onClose={handleCloseEvalInputsDialog} evalExecution={selectedEvalExecution} />
    </>
  );
};
