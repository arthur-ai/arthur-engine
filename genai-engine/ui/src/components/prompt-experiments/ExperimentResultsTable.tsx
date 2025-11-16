import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import {
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
} from "@mui/material";
import React, { useEffect, useState } from "react";

import { MessageDisplay, VariableTile } from "./PromptResultComponents";

import { useExperimentTestCases } from "@/hooks/usePromptExperiments";
import type { TestCase } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ExperimentResultsTableProps {
  taskId: string;
  experimentId: string;
  promptSummaries?: Array<{
    prompt_name: string;
    prompt_version: string;
    eval_results: Array<{
      eval_name: string;
      eval_version: string;
      pass_count: number;
      total_count: number;
    }>;
  }>;
  refreshTrigger?: number;
}

interface TestCaseDetailModalProps {
  testCase: TestCase | null;
  open: boolean;
  onClose: () => void;
  currentIndex: number;
  totalCount: number;
  onPrevious: () => void;
  onNext: () => void;
}

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps> = ({
  testCase,
  open,
  onClose,
  currentIndex,
  totalCount,
  onPrevious,
  onNext,
}) => {
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

  // Add keyboard navigation
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
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="test-case-detail-modal"
    >
      <Box
        className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-6xl max-h-[90vh] bg-white rounded-lg shadow-xl overflow-auto"
      >
        {/* Modal Header */}
        <Box className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center z-10">
          <Box className="flex items-center gap-3">
            <IconButton
              onClick={onPrevious}
              size="small"
              disabled={currentIndex <= 0}
              className="hover:bg-gray-100"
            >
              <ArrowBackIcon />
            </IconButton>
            <Typography variant="h6" className="font-semibold text-gray-900">
              Test Case {currentIndex + 1} of {totalCount}
            </Typography>
            <IconButton
              onClick={onNext}
              size="small"
              disabled={currentIndex >= totalCount - 1}
              className="hover:bg-gray-100"
            >
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
            <Typography
              variant="h6"
              className="font-bold mb-4 pb-2 border-b-2 border-gray-300 text-gray-900"
            >
              Input Variables
            </Typography>
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {testCase.prompt_input_variables.map((variable) => (
                <VariableTile
                  key={variable.variable_name}
                  variableName={variable.variable_name}
                  value={variable.value}
                />
              ))}
            </Box>
          </Box>

          {/* Prompt Results Section */}
          <Box>
            <Typography
              variant="h6"
              className="font-bold mb-4 pb-2 border-b-2 border-gray-300 text-gray-900"
            >
              Prompt Results
            </Typography>
            <Box className="space-y-4">
              {testCase.prompt_results.map((promptResult, index) => (
                <Card key={index} elevation={2}>
                  {/* Prompt Header */}
                  <Box className="bg-indigo-100 border-b border-indigo-200 px-4 py-3 flex items-center justify-between">
                    <Typography variant="h6" className="font-semibold text-indigo-900">
                      {promptResult.name} v{promptResult.version}
                    </Typography>
                    {promptResult.output && (
                      <Chip
                        label={`Cost: $${promptResult.output.cost}`}
                        size="small"
                        className="bg-white"
                      />
                    )}
                  </Box>

                  <CardContent>

                    {/* Messages: Rendered Prompt and Output */}
                    <Box className="grid grid-cols-2 gap-4 mb-4">
                      {/* Rendered Prompt Messages */}
                      <Box>
                        <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                          Input Messages:
                        </Typography>
                        <Box className="max-h-96 overflow-auto">
                          {(() => {
                            try {
                              const messages = JSON.parse(promptResult.rendered_prompt) as Message[];
                              return messages.map((message, msgIndex) => (
                                <MessageDisplay key={msgIndex} message={message} />
                              ));
                            } catch {
                              // If not JSON, display as plain text
                              return (
                                <Box className="p-3 bg-gray-100 border border-gray-300 rounded">
                                  <Typography variant="body2" className="whitespace-pre-wrap text-gray-900">
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
                        <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                          Output Message:
                        </Typography>
                        <Box className="max-h-96 overflow-auto">
                          {promptResult.output ? (
                            <>
                              <MessageDisplay
                                message={{ role: "assistant", content: promptResult.output.content }}
                              />
                              {promptResult.output.tool_calls && promptResult.output.tool_calls.length > 0 && (
                                <Box className="mt-2 p-2 bg-purple-50 border border-purple-200 rounded">
                                  <Typography variant="caption" className="font-medium text-purple-700">
                                    Tool Calls: {promptResult.output.tool_calls.length}
                                  </Typography>
                                </Box>
                              )}
                            </>
                          ) : (
                            <Box className="p-3 bg-gray-100 border border-gray-300 rounded">
                              <Typography variant="body2" className="text-gray-500 italic">
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
                        <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                          Evaluations:
                        </Typography>
                        <Box className="space-y-2">
                          {promptResult.evals.map((evalItem, evalIndex) => (
                            <Box key={evalIndex} className="p-3 bg-blue-50 border border-blue-200 rounded">
                              <Box className="flex items-center gap-2 mb-2">
                                <Typography variant="body2" className="font-medium text-gray-900">
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
                                      label={`Cost: $${evalItem.eval_results.cost}`}
                                      size="small"
                                      variant="outlined"
                                    />
                                  </>
                                ) : (
                                  <Chip
                                    label="Pending"
                                    size="small"
                                    sx={getPendingChipSx()}
                                  />
                                )}
                              </Box>
                              {evalItem.eval_results?.explanation && (
                                <Typography variant="body2" className="text-gray-700 mt-1">
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
              ))}
            </Box>
          </Box>
        </Box>
      </Box>
    </Modal>
  );
};

interface PromptEvalColumn {
  promptName: string;
  promptVersion: string;
  evalName: string;
  evalVersion: string;
}

interface EvalGroup {
  evalName: string;
  evalVersion: string;
  promptVersions: Array<{ promptName: string; promptVersion: string }>;
}

interface RowProps {
  testCase: TestCase;
  promptEvalColumns: PromptEvalColumn[];
  evalGroups: EvalGroup[];
  onClick: () => void;
}

const TestCaseRow: React.FC<RowProps> = ({ testCase, promptEvalColumns, evalGroups, onClick }) => {

  const getStatusColor = (
    status: TestCase["status"]
  ): "default" | "primary" | "info" | "success" | "error" => {
    switch (status) {
      case "queued":
        return "default";
      case "running":
        return "primary";
      case "evaluating":
        return "info";
      case "completed":
        return "success";
      case "failed":
        return "error";
      default:
        return "default";
    }
  };

  const getStatusLabel = (status: TestCase["status"]): string => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const getStatusChipSx = (color: "default" | "primary" | "info" | "success" | "error") => {
    const colorMap = {
      default: { color: "text.secondary", borderColor: "text.secondary" },
      primary: { color: "primary.main", borderColor: "primary.main" },
      info: { color: "info.main", borderColor: "info.main" },
      success: { color: "success.main", borderColor: "success.main" },
      error: { color: "error.main", borderColor: "error.main" },
    };
    return {
      backgroundColor: "transparent",
      color: colorMap[color].color,
      borderColor: colorMap[color].borderColor,
      borderWidth: 1,
      borderStyle: "solid",
    };
  };

  return (
    <TableRow
      hover
      onClick={onClick}
      sx={{ cursor: "pointer" }}
    >
      <TableCell>
        <Chip
          label={getStatusLabel(testCase.status)}
          size="small"
          sx={getStatusChipSx(getStatusColor(testCase.status))}
        />
      </TableCell>
      {promptEvalColumns.map((column, index) => {
        const promptResult = testCase.prompt_results.find(
          (pr) => pr.name === column.promptName && pr.version === column.promptVersion
        );
        const evalResult = promptResult?.evals.find(
          (e) => e.eval_name === column.evalName && e.eval_version === column.evalVersion
        );

        const score = evalResult?.eval_results?.score;
        const isPending = !evalResult?.eval_results;

        // Check if this is the last eval in its prompt group
        const isLastInGroup =
          index === promptEvalColumns.length - 1 ||
          promptEvalColumns[index + 1].promptName !== column.promptName ||
          promptEvalColumns[index + 1].promptVersion !== column.promptVersion;

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
          const promptResult = testCase.prompt_results.find(
            (pr) => pr.name === promptVersion.promptName && pr.version === promptVersion.promptVersion
          );
          const evalResult = promptResult?.evals.find(
            (e) => e.eval_name === evalGroup.evalName && e.eval_version === evalGroup.evalVersion
          );

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
              backgroundColor: "#f9fafb",
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
      <TableCell align="right">
        {testCase.total_cost ? formatCurrency(parseFloat(testCase.total_cost)) : "-"}
      </TableCell>
    </TableRow>
  );
};

export const ExperimentResultsTable: React.FC<ExperimentResultsTableProps> = ({
  taskId,
  experimentId,
  promptSummaries = [],
  refreshTrigger,
}) => {
  const [page, setPage] = useState(0);
  const pageSize = 20;
  const { testCases, totalPages, totalCount, isLoading, error, refetch } = useExperimentTestCases(experimentId, page, pageSize);
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(-1);
  const [modalOpen, setModalOpen] = useState(false);
  const [pendingIndexAfterPageLoad, setPendingIndexAfterPageLoad] = useState<"first" | "last" | null>(null);

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
        summary.eval_results.forEach((evalResult) => {
          columns.push({
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
      const promptMap = new Map<string, {
        promptName: string;
        promptVersion: string;
        evals: Array<{ evalName: string; evalVersion: string }>;
      }>();

      testCases.forEach((tc) => {
        tc.prompt_results.forEach((pr) => {
          const promptKey = `${pr.name}-${pr.version}`;
          if (!promptMap.has(promptKey)) {
            promptMap.set(promptKey, {
              promptName: pr.name,
              promptVersion: pr.version,
              evals: [],
            });
          }
          const promptData = promptMap.get(promptKey)!;
          pr.evals.forEach((e) => {
            const evalExists = promptData.evals.some(
              (ev) => ev.evalName === e.eval_name && ev.evalVersion === e.eval_version
            );
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
    const groups = new Map<string, { promptName: string; promptVersion: string; evalCount: number }>();
    promptEvalColumns.forEach((col) => {
      const key = `${col.promptName}-${col.promptVersion}`;
      if (!groups.has(key)) {
        groups.set(key, {
          promptName: col.promptName,
          promptVersion: col.promptVersion,
          evalCount: 0,
        });
      }
      groups.get(key)!.evalCount++;
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
      const promptExists = group.promptVersions.some(
        (pv) => pv.promptName === col.promptName && pv.promptVersion === col.promptVersion
      );
      if (!promptExists) {
        group.promptVersions.push({
          promptName: col.promptName,
          promptVersion: col.promptVersion,
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
      <TableContainer component={Paper} sx={{ flexGrow: 0, flexShrink: 1 }}>
        {isLoading && <LinearProgress />}
        <Table stickyHeader size="small" aria-label="experiment results table">
          <TableHead>
            {/* Top header row: Prompt versions and Totals */}
            <TableRow>
              <TableCell
                rowSpan={2}
                sx={{ backgroundColor: "grey.50", borderRight: 1, borderColor: "divider" }}
              >
                <Box component="span" className="font-semibold">
                  Status
                </Box>
              </TableCell>
              {promptGroups.map((group, index) => (
                <TableCell
                  key={`${group.promptName}-${group.promptVersion}`}
                  colSpan={group.evalCount}
                  align="center"
                  sx={{
                    backgroundColor: "grey.50",
                    borderRight: index === promptGroups.length - 1 ? 3 : 1,
                    borderColor: "divider",
                  }}
                >
                  <Box component="span" className="font-semibold">
                    {group.promptName} (v{group.promptVersion})
                  </Box>
                </TableCell>
              ))}
              <TableCell
                colSpan={evalGroups.length}
                align="center"
                sx={{
                  backgroundColor: "grey.50",
                  borderRight: 3,
                  borderColor: "divider",
                }}
              >
                <Box component="span" className="font-semibold">
                  Totals
                </Box>
              </TableCell>
              <TableCell
                rowSpan={2}
                align="right"
                sx={{ backgroundColor: "grey.50", borderLeft: 1, borderColor: "divider" }}
              >
                <Box component="span" className="font-semibold">
                  Cost
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
                      backgroundColor: "grey.50",
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
                    backgroundColor: "grey.50",
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
                <TableCell colSpan={2 + promptEvalColumns.length + evalGroups.length} align="center">
                  <Typography>Loading results...</Typography>
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={2 + promptEvalColumns.length + evalGroups.length} align="center">
                  <Typography color="error">{error.message}</Typography>
                </TableCell>
              </TableRow>
            ) : testCases.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2 + promptEvalColumns.length + evalGroups.length} align="center">
                  <Typography className="text-gray-600">No test cases found</Typography>
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
                />
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {totalPages > 1 && (
        <Box className="flex justify-center mt-4">
          <Pagination
            count={totalPages}
            page={page + 1}
            onChange={handlePageChange}
            color="primary"
          />
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
      />
    </Box>
  );
};
