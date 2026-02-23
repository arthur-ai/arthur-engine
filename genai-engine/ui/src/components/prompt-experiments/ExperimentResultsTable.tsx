import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import SaveAltIcon from "@mui/icons-material/SaveAlt";
import VisibilityIcon from "@mui/icons-material/Visibility";
import {
  Alert,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Chip,
  Card,
  CardContent,
  Pagination,
  Modal,
  IconButton,
  LinearProgress,
  CircularProgress,
  Button,
  Snackbar,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import React, { useEffect, useState } from "react";

import { MessageDisplay, VariableTile } from "./PromptResultComponents";
import { EvalInputsDialog } from "./PromptResultDetailModal";

import { UpdateDatasetRowModal } from "@/components/common/UpdateDatasetRowModal";
import { useApi } from "@/hooks/useApi";
import { useExperimentTestCases } from "@/hooks/usePromptExperiments";
import useSnackbar from "@/hooks/useSnackbar";
import type { TestCase, DatasetVersionRowResponse, EvalExecution } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ExperimentResultsTableProps {
  experimentId: string;
  promptSummaries?: Array<{
    prompt_key?: string | null;
    prompt_type?: string | null;
    prompt_name?: string | null;
    prompt_version?: string | null;
    eval_results: Array<{
      eval_name: string;
      eval_version: string;
      pass_count: number;
      total_count: number;
    }>;
  }>;
  refreshTrigger?: number;
  datasetId?: string;
  datasetVersion?: number;
}

interface TestCaseDetailModalProps {
  testCase: TestCase | null;
  open: boolean;
  onClose: () => void;
  currentIndex: number;
  totalCount: number;
  onPrevious: () => void;
  onNext: () => void;
  onViewEvalInputs?: (evalExecution: EvalExecution) => void;
  datasetId?: string;
  datasetVersion?: number;
}

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps> = ({
  testCase,
  open,
  onClose,
  currentIndex,
  totalCount,
  onPrevious,
  onNext,
  onViewEvalInputs,
  datasetId,
  datasetVersion,
}) => {
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [selectedOutputForUpdate, setSelectedOutputForUpdate] = useState<string | null>(null);
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const canUpdateDataset = !!(datasetId && datasetVersion !== undefined && testCase?.dataset_row_id);

  const handleOpenUpdateModal = (outputContent: string) => {
    setSelectedOutputForUpdate(outputContent);
    setUpdateModalOpen(true);
  };

  const handleUpdateSuccess = () => {
    showSnackbar("Dataset updated successfully. New version created.", "success");
    setUpdateModalOpen(false);
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

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!open) return;

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
  }, [open, onPrevious, onNext]);

  if (!testCase) return null;

  return (
    <Modal open={open} onClose={onClose} aria-labelledby="test-case-detail-modal">
      <Box className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-6xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-lg shadow-xl overflow-auto">
        {/* Modal Header */}
        <Box className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center z-10">
          <Box className="flex items-center gap-3">
            <IconButton onClick={onPrevious} size="small" disabled={currentIndex <= 0} className="hover:bg-gray-100 dark:hover:bg-gray-800">
              <ArrowBackIcon />
            </IconButton>
            <Typography variant="h6" className="font-semibold text-gray-900 dark:text-gray-100">
              Test Case {currentIndex + 1} of {totalCount}
            </Typography>
            <IconButton onClick={onNext} size="small" disabled={currentIndex >= totalCount - 1} className="hover:bg-gray-100 dark:hover:bg-gray-800">
              <ArrowForwardIcon />
            </IconButton>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Modal Content */}
        <Box className="p-6">
          {/* Input Variables Section */}
          <Box className="mb-6">
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, pb: 1, borderBottom: 2, borderColor: "divider", color: "text.primary" }}>
              Input Variables
            </Typography>
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {testCase.prompt_input_variables.map((variable) => (
                <VariableTile key={variable.variable_name} variableName={variable.variable_name} value={variable.value} />
              ))}
            </Box>
          </Box>

          {/* Prompt Results Section */}
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, pb: 1, borderBottom: 2, borderColor: "divider", color: "text.primary" }}>
              Prompt Results
            </Typography>
            <Box className="space-y-4">
              {testCase.prompt_results.map((promptResult, index) => {
                const promptDisplayName =
                  promptResult.name && promptResult.version ? `${promptResult.name} v${promptResult.version}` : promptResult.name || "Unsaved Prompt";

                return (
                  <Card key={index} elevation={2}>
                    {/* Prompt Header */}
                    <Box className="bg-indigo-100 border-b border-indigo-200 px-4 py-3 flex items-center justify-between">
                      <Typography variant="h6" className="font-semibold text-indigo-900">
                        {promptDisplayName}
                      </Typography>
                      {promptResult.output && (
                        <Chip label={`Cost: $${promptResult.output.cost}`} size="small" className="bg-white dark:bg-gray-900" />
                      )}
                    </Box>

                    <CardContent>
                      {/* Messages: Rendered Prompt and Output */}
                      <Box className="grid grid-cols-2 gap-4 mb-4">
                        {/* Rendered Prompt Messages */}
                        <Box>
                          <Typography variant="subtitle2" className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Input Messages:
                          </Typography>
                          <Box className="max-h-96 overflow-auto">
                            {(() => {
                              try {
                                const messages = JSON.parse(promptResult.rendered_prompt) as Message[];
                                return messages.map((message, msgIndex) => <MessageDisplay key={msgIndex} message={message} />);
                              } catch {
                                // If not JSON, display as plain text
                                return (
                                  <Box
                                    sx={{
                                      p: 1.5,
                                      backgroundColor: "action.hover",
                                      border: 1,
                                      borderColor: "divider",
                                      borderRadius: 1,
                                    }}
                                  >
                                    <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", color: "text.primary" }}>
                                      {promptResult.rendered_prompt}
                                    </Typography>
                                  </Box>
                                );
                              }
                            })()}
                          </Box>
                        </Box>

                        {/* Output */}
                        <Box>
                          <Box className="flex items-center justify-between mb-2">
                            <Typography variant="subtitle2" className="font-medium text-gray-700 dark:text-gray-300">
                              Output Message:
                            </Typography>
                            {canUpdateDataset && promptResult.output?.content && (
                              <Button
                                size="small"
                                variant="outlined"
                                startIcon={<SaveAltIcon />}
                                onClick={() => handleOpenUpdateModal(promptResult.output!.content)}
                                title="Update dataset row with this output"
                              >
                                Update Dataset
                              </Button>
                            )}
                          </Box>
                          <Box className="max-h-96 overflow-auto">
                            {promptResult.output ? (
                              <>
                                <MessageDisplay message={{ role: "assistant", content: promptResult.output.content }} />
                                {promptResult.output.tool_calls && promptResult.output.tool_calls.length > 0 && (
                                  <Box
                                    sx={(theme) => ({
                                      mt: 1,
                                      p: 1,
                                      bgcolor: alpha(theme.palette.secondary.main, 0.08),
                                      border: `1px solid ${alpha(theme.palette.secondary.main, 0.3)}`,
                                      borderRadius: 1,
                                    })}
                                  >
                                    <Typography variant="caption" sx={{ fontWeight: 500, color: "secondary.main" }}>
                                      Tool Calls: {promptResult.output.tool_calls.length}
                                    </Typography>
                                  </Box>
                                )}
                              </>
                            ) : (
                              <Box
                                sx={{
                                  p: 1.5,
                                  backgroundColor: "action.hover",
                                  border: 1,
                                  borderColor: "divider",
                                  borderRadius: 1,
                                }}
                              >
                                <Typography variant="body2" sx={{ color: "text.secondary", fontStyle: "italic" }}>
                                  No output available
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        </Box>
                      </Box>

                      {/* Evals */}
                      {promptResult.evals.length > 0 && (
                        <Box>
                          <Typography variant="subtitle2" className="font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Evaluations:
                          </Typography>
                          <Box className="space-y-2">
                            {promptResult.evals.map((evalItem, evalIndex) => (
                              <Box
                                key={evalIndex}
                                sx={(theme) => ({
                                  p: 1.5,
                                  backgroundColor: alpha(theme.palette.info.main, 0.08),
                                  border: `1px solid ${alpha(theme.palette.info.main, 0.3)}`,
                                  borderRadius: 1,
                                })}
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
                                        <Chip label={`Cost: $${evalItem.eval_results.cost}`} size="small" variant="outlined" />
                                      </>
                                    ) : (
                                      <Chip label="Pending" size="small" sx={getPendingChipSx()} />
                                    )}
                                  </Box>
                                  {onViewEvalInputs && (
                                    <Button
                                      size="small"
                                      variant="outlined"
                                      startIcon={<InfoOutlinedIcon />}
                                      onClick={() => onViewEvalInputs(evalItem)}
                                    >
                                      View Inputs
                                    </Button>
                                  )}
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

        {canUpdateDataset && selectedOutputForUpdate && (
          <UpdateDatasetRowModal
            open={updateModalOpen}
            onClose={() => setUpdateModalOpen(false)}
            datasetId={datasetId!}
            datasetVersion={datasetVersion!}
            rowId={testCase.dataset_row_id}
            outputValue={selectedOutputForUpdate}
            onSuccess={handleUpdateSuccess}
          />
        )}

        <Snackbar {...snackbarProps}>
          <Alert {...alertProps} />
        </Snackbar>
      </Box>
    </Modal>
  );
};

interface PromptEvalColumn {
  promptKey: string;
  promptName?: string | null;
  promptVersion?: string | null;
  evalName: string;
  evalVersion: string;
}

interface EvalGroup {
  evalName: string;
  evalVersion: string;
  promptVersions: Array<{ promptKey: string }>;
}

interface RowProps {
  testCase: TestCase;
  promptEvalColumns: PromptEvalColumn[];
  evalGroups: EvalGroup[];
  onClick: () => void;
  onViewData?: () => void;
}

const TestCaseRow: React.FC<RowProps> = ({ testCase, promptEvalColumns, evalGroups, onClick, onViewData }) => {
  return (
    <TableRow hover onClick={onClick} sx={{ cursor: "pointer" }}>
      <TableCell>
        <Chip label={testCase.status} size="small" sx={getStatusChipSx(testCase.status)} />
      </TableCell>
      {promptEvalColumns.map((column, index) => {
        const promptResult = testCase.prompt_results.find((pr) => pr.prompt_key === column.promptKey);
        const evalResult = promptResult?.evals.find((e) => e.eval_name === column.evalName && e.eval_version === column.evalVersion);

        const score = evalResult?.eval_results?.score;
        const isPending = !evalResult?.eval_results;

        // Check if this is the last eval in its prompt group
        const isLastInGroup = index === promptEvalColumns.length - 1 || promptEvalColumns[index + 1].promptKey !== column.promptKey;

        return (
          <TableCell
            key={`${column.promptName}-${column.promptVersion}-${column.evalName}-${column.evalVersion}`}
            align="center"
            sx={{
              padding: "6px 8px",
              borderRight: isLastInGroup ? (index === promptEvalColumns.length - 1 ? 3 : 0) : 0,
              borderColor: "divider",
            }}
          >
            {isPending ? (
              <CircularProgress size={16} sx={{ color: "text.secondary" }} />
            ) : score === 1 ? (
              <Box
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "20px",
                  height: "20px",
                  color: "#6b7280",
                  fontWeight: 600,
                  fontSize: "0.8rem",
                }}
              >
                ✓
              </Box>
            ) : (
              <Box
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "20px",
                  height: "20px",
                  color: "#ef4444",
                  fontWeight: 600,
                  fontSize: "0.8rem",
                }}
              >
                ✕
              </Box>
            )}
          </TableCell>
        );
      })}
      {/* Eval totals columns */}
      {evalGroups.map((evalGroup, index) => {
        let passCount = 0;
        let totalCount = 0;

        evalGroup.promptVersions.forEach((promptVersion) => {
          const promptResult = testCase.prompt_results.find((pr) => pr.prompt_key === promptVersion.promptKey);
          const evalResult = promptResult?.evals.find((e) => e.eval_name === evalGroup.evalName && e.eval_version === evalGroup.evalVersion);

          if (evalResult?.eval_results) {
            totalCount++;
            if (evalResult.eval_results.score === 1) {
              passCount++;
            }
          }
        });

        return (
          <TableCell
            key={`total-${evalGroup.evalName}-${evalGroup.evalVersion}`}
            align="center"
            sx={{
              backgroundColor: "background.default",
              fontWeight: 500,
              fontSize: "0.8rem",
              borderRight: index === evalGroups.length - 1 ? 3 : 0,
              borderColor: "divider",
            }}
          >
            <Typography
              variant="body2"
              sx={{
                fontSize: "0.8rem",
                fontWeight: 500,
                color: passCount === 0 && totalCount > 0 ? "#ef4444" : "#6b7280",
              }}
            >
              {passCount}/{totalCount}
            </Typography>
          </TableCell>
        );
      })}
      <TableCell align="right">{testCase.total_cost ? formatCurrency(parseFloat(testCase.total_cost)) : "-"}</TableCell>
      <TableCell align="center" onClick={(e) => e.stopPropagation()}>
        {onViewData && (
          <IconButton size="small" onClick={onViewData} title="View dataset row">
            <VisibilityIcon fontSize="small" />
          </IconButton>
        )}
      </TableCell>
    </TableRow>
  );
};

interface DatasetRowModalProps {
  open: boolean;
  onClose: () => void;
  datasetId: string;
  versionNumber: number;
  rowId: string;
}

const DatasetRowModal: React.FC<DatasetRowModalProps> = ({ open, onClose, datasetId, versionNumber, rowId }) => {
  const [rowData, setRowData] = useState<DatasetVersionRowResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const api = useApi();

  useEffect(() => {
    if (!open || !api) return;

    const fetchRowData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.api.getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet(datasetId, versionNumber, rowId);
        setRowData(response.data);
      } catch (err) {
        console.error("Failed to fetch dataset row:", err);
        setError(err instanceof Error ? err.message : "Failed to load dataset row");
      } finally {
        setLoading(false);
      }
    };

    fetchRowData();
  }, [open, api, datasetId, versionNumber, rowId]);

  return (
    <Modal open={open} onClose={onClose} aria-labelledby="dataset-row-modal">
      <Box className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-4xl max-h-[80vh] bg-white dark:bg-gray-900 rounded-lg shadow-xl overflow-auto">
        {/* Modal Header */}
        <Box className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex justify-between items-center z-10">
          <Typography variant="h6" className="font-semibold text-gray-900 dark:text-gray-100">
            Dataset Row Data
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Modal Content */}
        <Box className="p-6">
          {loading ? (
            <Box className="flex justify-center items-center py-8">
              <CircularProgress />
            </Box>
          ) : error ? (
            <Box className="flex justify-center items-center py-8">
              <Typography color="error">{error}</Typography>
            </Box>
          ) : rowData ? (
            <Box>
              <Box className="mb-4">
                <Typography variant="body2" className="text-gray-600 dark:text-gray-400 mb-2">
                  Dataset: {datasetId} | Version: {versionNumber} | Row ID: {rowId}
                </Typography>
              </Box>
              <Box className="space-y-3">
                {rowData.data.map((item, index) => (
                  <Box key={index} className="p-4 bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
                    <Typography variant="subtitle2" className="font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      {item.column_name}
                    </Typography>
                    <Typography variant="body2" className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap wrap-break-word">
                      {item.column_value}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          ) : null}
        </Box>
      </Box>
    </Modal>
  );
};

export const ExperimentResultsTable: React.FC<ExperimentResultsTableProps> = ({
  experimentId,
  promptSummaries = [],
  refreshTrigger,
  datasetId,
  datasetVersion,
}) => {
  const [page, setPage] = useState(0);
  const pageSize = 20;
  const { testCases, totalPages, totalCount, isLoading, error, refetch } = useExperimentTestCases(experimentId, page, pageSize);
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(-1);
  const [modalOpen, setModalOpen] = useState(false);
  const [pendingIndexAfterPageLoad, setPendingIndexAfterPageLoad] = useState<"first" | "last" | null>(null);
  const [evalInputsDialogOpen, setEvalInputsDialogOpen] = useState(false);
  const [selectedEvalExecution, setSelectedEvalExecution] = useState<EvalExecution | null>(null);
  const [datasetRowModalOpen, setDatasetRowModalOpen] = useState(false);
  const [selectedDatasetRow, setSelectedDatasetRow] = useState<{ datasetId: string; versionNumber: number; rowId: string } | null>(null);

  // Refetch test cases when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger !== undefined) {
      refetch();
    }
  }, [refreshTrigger, refetch]);

  // Effect to handle index after page load
  useEffect(() => {
    if (pendingIndexAfterPageLoad && testCases.length > 0) {
      if (pendingIndexAfterPageLoad === "first") {
        setSelectedTestCaseIndex(0);
      } else if (pendingIndexAfterPageLoad === "last") {
        setSelectedTestCaseIndex(testCases.length - 1);
      }
      setPendingIndexAfterPageLoad(null);
    }
  }, [testCases, pendingIndexAfterPageLoad]);

  const handleRowClick = (index: number) => {
    setSelectedTestCaseIndex(index);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedTestCaseIndex(-1);
  };

  const handleViewEvalInputs = (evalExecution: EvalExecution) => {
    setSelectedEvalExecution(evalExecution);
    setEvalInputsDialogOpen(true);
  };

  const handleCloseEvalInputsDialog = () => {
    setEvalInputsDialogOpen(false);
    setSelectedEvalExecution(null);
  };

  const handleViewDatasetRow = (testCase: TestCase, datasetId: string, versionNumber: number) => {
    setSelectedDatasetRow({
      datasetId,
      versionNumber,
      rowId: testCase.dataset_row_id,
    });
    setDatasetRowModalOpen(true);
  };

  const handleCloseDatasetRowModal = () => {
    setDatasetRowModalOpen(false);
    setSelectedDatasetRow(null);
  };

  const handlePrevious = async () => {
    if (selectedTestCaseIndex > 0) {
      // Navigate within current page
      setSelectedTestCaseIndex(selectedTestCaseIndex - 1);
    } else if (page > 0) {
      // Load previous page and go to last item
      setPendingIndexAfterPageLoad("last");
      setPage(page - 1);
    }
  };

  const handleNext = async () => {
    if (selectedTestCaseIndex < testCases.length - 1) {
      // Navigate within current page
      setSelectedTestCaseIndex(selectedTestCaseIndex + 1);
    } else if (page < totalPages - 1) {
      // Load next page and go to first item
      setPendingIndexAfterPageLoad("first");
      setPage(page + 1);
    }
  };

  // Calculate global index for display
  const globalIndex = page * pageSize + selectedTestCaseIndex;

  // Build prompt-eval columns from promptSummaries (already sorted by performance)
  // If promptSummaries not provided, fall back to extracting from test cases
  const promptEvalColumns = React.useMemo(() => {
    if (promptSummaries.length > 0) {
      // Use provided sorted summaries
      const columns: PromptEvalColumn[] = [];
      promptSummaries.forEach((summary) => {
        const promptKey =
          summary.prompt_key ||
          (summary.prompt_name && summary.prompt_version ? `saved:${summary.prompt_name}:${summary.prompt_version}` : `unknown`);
        summary.eval_results.forEach((evalResult) => {
          columns.push({
            promptKey: promptKey,
            promptName: summary.prompt_name,
            promptVersion: summary.prompt_version,
            evalName: evalResult.eval_name,
            evalVersion: evalResult.eval_version,
          });
        });
      });
      return columns;
    } else {
      // Fallback: extract from test cases
      const promptMap = new Map<
        string,
        {
          promptKey: string;
          promptName: string | null | undefined;
          promptVersion: string | null | undefined;
          evals: Array<{ evalName: string; evalVersion: string }>;
        }
      >();

      testCases.forEach((tc) => {
        tc.prompt_results.forEach((pr) => {
          if (!promptMap.has(pr.prompt_key)) {
            promptMap.set(pr.prompt_key, {
              promptKey: pr.prompt_key,
              promptName: pr.name ?? null,
              promptVersion: pr.version ?? null,
              evals: [],
            });
          }
          const promptData = promptMap.get(pr.prompt_key)!;
          pr.evals.forEach((e) => {
            const evalExists = promptData.evals.some((ev) => ev.evalName === e.eval_name && ev.evalVersion === e.eval_version);
            if (!evalExists) {
              promptData.evals.push({
                evalName: e.eval_name,
                evalVersion: e.eval_version,
              });
            }
          });
        });
      });

      const columns: PromptEvalColumn[] = [];
      promptMap.forEach((promptData) => {
        promptData.evals.forEach((evalData) => {
          columns.push({
            promptKey: promptData.promptKey,
            promptName: promptData.promptName,
            promptVersion: promptData.promptVersion,
            evalName: evalData.evalName,
            evalVersion: evalData.evalVersion,
          });
        });
      });
      return columns;
    }
  }, [testCases, promptSummaries]);

  // Group columns by prompt for the header
  const promptGroups = React.useMemo(() => {
    const groups = new Map<string, { promptKey: string; promptName?: string | null; promptVersion?: string | null; evalCount: number }>();
    promptEvalColumns.forEach((col) => {
      if (!groups.has(col.promptKey)) {
        groups.set(col.promptKey, {
          promptKey: col.promptKey,
          promptName: col.promptName ?? null,
          promptVersion: col.promptVersion ?? null,
          evalCount: 0,
        });
      }
      groups.get(col.promptKey)!.evalCount++;
    });
    return Array.from(groups.values());
  }, [promptEvalColumns]);

  // Build eval groups for totals columns
  const evalGroups = React.useMemo(() => {
    const groups = new Map<string, EvalGroup>();
    promptEvalColumns.forEach((col) => {
      const key = `${col.evalName}-${col.evalVersion}`;
      if (!groups.has(key)) {
        groups.set(key, {
          evalName: col.evalName,
          evalVersion: col.evalVersion,
          promptVersions: [],
        });
      }
      const group = groups.get(key)!;
      const promptExists = group.promptVersions.some((pv) => pv.promptKey === col.promptKey);
      if (!promptExists) {
        group.promptVersions.push({
          promptKey: col.promptKey,
        });
      }
    });
    return Array.from(groups.values());
  }, [promptEvalColumns]);

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    // Convert from 1-based MUI Pagination to 0-based internal state
    setPage(value - 1);
  };

  return (
    <Box>
      <TableContainer component={Paper} elevation={1} sx={{ flexGrow: 0, flexShrink: 1 }}>
        {isLoading && <LinearProgress />}
        <Table stickyHeader size="small" aria-label="experiment results table">
          <TableHead>
            {/* Top header row: Prompt versions and Totals */}
            <TableRow>
              <TableCell rowSpan={2} sx={{ borderRight: 1, borderColor: "divider" }}>
                <Box component="span" className="font-semibold">
                  Status
                </Box>
              </TableCell>
              {promptGroups.map((group, index) => {
                const displayName =
                  group.promptName && group.promptVersion ? `${group.promptName} (v${group.promptVersion})` : group.promptName || "Unsaved Prompt";

                return (
                  <TableCell
                    key={group.promptKey}
                    colSpan={group.evalCount}
                    align="center"
                    sx={{
                      borderRight: index === promptGroups.length - 1 ? 3 : 1,
                      borderColor: "divider",
                    }}
                  >
                    <Box component="span" className="font-semibold">
                      {displayName}
                    </Box>
                  </TableCell>
                );
              })}
              <TableCell
                colSpan={evalGroups.length}
                align="center"
                sx={{
                  borderRight: 3,
                  borderColor: "divider",
                }}
              >
                <Box component="span" className="font-semibold">
                  Totals
                </Box>
              </TableCell>
              <TableCell rowSpan={2} align="right" sx={{ borderLeft: 1, borderColor: "divider" }}>
                <Box component="span" className="font-semibold">
                  Cost
                </Box>
              </TableCell>
              <TableCell rowSpan={2} align="center" sx={{ borderLeft: 1, borderColor: "divider" }}>
                <Box component="span" className="font-semibold">
                  View Data
                </Box>
              </TableCell>
            </TableRow>
            {/* Bottom header row: Evaluators */}
            <TableRow>
              {promptEvalColumns.map((col, index) => {
                // Check if this is the last eval in its prompt group
                const isLastInGroup =
                  index === promptEvalColumns.length - 1 ||
                  promptEvalColumns[index + 1].promptName !== col.promptName ||
                  promptEvalColumns[index + 1].promptVersion !== col.promptVersion;

                return (
                  <TableCell
                    key={`${col.promptName}-${col.promptVersion}-${col.evalName}-${col.evalVersion}`}
                    align="center"
                    sx={{
                      borderRight: isLastInGroup ? (index === promptEvalColumns.length - 1 ? 3 : 1) : 0,
                      borderColor: "divider",
                      fontSize: "0.75rem",
                    }}
                  >
                    <Box component="span" className="font-medium">
                      {col.evalName} (v{col.evalVersion})
                    </Box>
                  </TableCell>
                );
              })}
              {/* Totals sub-headers */}
              {evalGroups.map((evalGroup, index) => (
                <TableCell
                  key={`total-header-${evalGroup.evalName}-${evalGroup.evalVersion}`}
                  align="center"
                  sx={{
                    borderRight: index === evalGroups.length - 1 ? 3 : 0,
                    borderColor: "divider",
                    fontSize: "0.75rem",
                  }}
                >
                  <Box component="span" className="font-medium">
                    {evalGroup.evalName} (v{evalGroup.evalVersion})
                  </Box>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={3 + promptEvalColumns.length + evalGroups.length} align="center">
                  <Typography>Loading results...</Typography>
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={3 + promptEvalColumns.length + evalGroups.length} align="center">
                  <Typography color="error">{error.message}</Typography>
                </TableCell>
              </TableRow>
            ) : testCases.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3 + promptEvalColumns.length + evalGroups.length} align="center">
                  <Typography className="text-gray-600 dark:text-gray-400">No test cases found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              testCases.map((testCase, index) => (
                <TestCaseRow
                  key={testCase.dataset_row_id || index}
                  testCase={testCase}
                  promptEvalColumns={promptEvalColumns}
                  evalGroups={evalGroups}
                  onClick={() => handleRowClick(index)}
                  onViewData={datasetId && datasetVersion ? () => handleViewDatasetRow(testCase, datasetId, datasetVersion) : undefined}
                />
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {totalPages > 1 && (
        <Box className="flex justify-center mt-4">
          <Pagination count={totalPages} page={page + 1} onChange={handlePageChange} color="primary" />
        </Box>
      )}

      <TestCaseDetailModal
        testCase={selectedTestCaseIndex >= 0 ? testCases[selectedTestCaseIndex] : null}
        open={modalOpen}
        onClose={handleCloseModal}
        currentIndex={globalIndex}
        totalCount={totalCount}
        onPrevious={handlePrevious}
        onNext={handleNext}
        onViewEvalInputs={handleViewEvalInputs}
        datasetId={datasetId}
        datasetVersion={datasetVersion}
      />

      {/* Eval Inputs Dialog - rendered as sibling to avoid nesting in Modal */}
      <EvalInputsDialog open={evalInputsDialogOpen} onClose={handleCloseEvalInputsDialog} evalExecution={selectedEvalExecution} />

      {/* Dataset Row Modal */}
      {selectedDatasetRow && (
        <DatasetRowModal
          open={datasetRowModalOpen}
          onClose={handleCloseDatasetRowModal}
          datasetId={selectedDatasetRow.datasetId}
          versionNumber={selectedDatasetRow.versionNumber}
          rowId={selectedDatasetRow.rowId}
        />
      )}
    </Box>
  );
};
