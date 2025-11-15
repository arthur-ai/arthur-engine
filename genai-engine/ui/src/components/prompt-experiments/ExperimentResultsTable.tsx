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
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import React, { useEffect, useState } from "react";
import { useExperimentTestCases } from "@/hooks/usePromptExperiments";
import type { TestCase } from "@/lib/api-client/api-client";

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ExperimentResultsTableProps {
  taskId: string;
  experimentId: string;
}

interface MessageDisplayProps {
  message: Message;
}

const MessageDisplay: React.FC<MessageDisplayProps> = ({ message }) => {
  const getRoleStyles = (role: Message["role"]) => {
    switch (role) {
      case "system":
        return {
          bg: "bg-gray-100",
          border: "border-gray-300",
          label: "System",
          labelColor: "text-gray-700",
        };
      case "user":
        return {
          bg: "bg-blue-50",
          border: "border-blue-200",
          label: "User",
          labelColor: "text-blue-700",
        };
      case "assistant":
        return {
          bg: "bg-green-50",
          border: "border-green-200",
          label: "Assistant",
          labelColor: "text-green-700",
        };
      default:
        return {
          bg: "bg-gray-50",
          border: "border-gray-200",
          label: role,
          labelColor: "text-gray-700",
        };
    }
  };

  const styles = getRoleStyles(message.role);

  return (
    <Box className={`p-3 ${styles.bg} border ${styles.border} rounded mb-2`}>
      <Typography variant="caption" className={`font-semibold ${styles.labelColor} block mb-1`}>
        {styles.label}
      </Typography>
      <Typography variant="body2" className="whitespace-pre-wrap text-gray-900">
        {message.content}
      </Typography>
    </Box>
  );
};

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
            <Typography variant="subtitle1" className="font-semibold mb-3 text-gray-900">
              Input Variables
            </Typography>
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {testCase.prompt_input_variables.map((variable) => (
                <Box key={variable.variable_name} className="p-3 bg-gray-50 border border-gray-200 rounded">
                  <Typography variant="caption" className="font-medium text-gray-700">
                    {variable.variable_name}:
                  </Typography>
                  <Typography variant="body2" className="text-gray-900 mt-1">
                    {variable.value}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Box>

          {/* Prompt Results Section */}
          <Box>
            <Typography variant="subtitle1" className="font-semibold mb-3 text-gray-900">
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
                    <Chip
                      label={`Cost: $${promptResult.output.cost}`}
                      size="small"
                      className="bg-white"
                    />
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
                                <Chip
                                  label={evalItem.eval_results.score === 1 ? "Pass" : "Fail"}
                                  size="small"
                                  color={evalItem.eval_results.score === 1 ? "success" : "error"}
                                />
                                <Chip
                                  label={`Cost: $${evalItem.eval_results.cost.toFixed(4)}`}
                                  size="small"
                                  variant="outlined"
                                />
                              </Box>
                              {evalItem.eval_results.explanation && (
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

interface RowProps {
  testCase: TestCase;
  variableColumns: string[];
  evalColumns: Array<{ name: string; version: string }>;
  onClick: () => void;
}

const TestCaseRow: React.FC<RowProps> = ({ testCase, variableColumns, evalColumns, onClick }) => {

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

  // Create a map of variables for easy lookup
  const variableMap = testCase.prompt_input_variables.reduce((acc, variable) => {
    acc[variable.variable_name] = variable.value;
    return acc;
  }, {} as Record<string, string>);

  // Create a map of eval scores for easy lookup (averaging across all prompt versions)
  const evalScoreMap = evalColumns.reduce((acc, evalCol) => {
    const key = `${evalCol.name}-${evalCol.version}`;
    const scores: number[] = [];

    testCase.prompt_results.forEach((promptResult) => {
      const evalResult = promptResult.evals.find(
        (e) => e.eval_name === evalCol.name && e.eval_version === evalCol.version
      );
      if (evalResult) {
        scores.push(evalResult.eval_results.score);
      }
    });

    if (scores.length > 0) {
      const avgScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
      acc[key] = avgScore;
    }

    return acc;
  }, {} as Record<string, number>);

  return (
    <TableRow
      className="hover:bg-gray-50 cursor-pointer"
      onClick={onClick}
    >
      <TableCell>
        <Chip
          label={getStatusLabel(testCase.status)}
          color={getStatusColor(testCase.status)}
          size="small"
        />
      </TableCell>
      {evalColumns.map((evalCol) => {
        const key = `${evalCol.name}-${evalCol.version}`;
        const score = evalScoreMap[key];
        return (
          <TableCell key={key}>
            {score !== undefined ? (
              <Typography variant="body2" className="font-medium">
                {score}
              </Typography>
            ) : (
              <Typography variant="body2" className="text-gray-400">
                -
              </Typography>
            )}
          </TableCell>
        );
      })}
      {variableColumns.map((varName) => (
        <TableCell key={varName}>
          <Typography variant="body2" className="truncate max-w-xs">
            {variableMap[varName] || "-"}
          </Typography>
        </TableCell>
      ))}
    </TableRow>
  );
};

export const ExperimentResultsTable: React.FC<ExperimentResultsTableProps> = ({
  taskId,
  experimentId,
}) => {
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const { testCases, totalPages, totalCount, isLoading, error } = useExperimentTestCases(experimentId, page, pageSize);
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(-1);
  const [modalOpen, setModalOpen] = useState(false);
  const [pendingIndexAfterPageLoad, setPendingIndexAfterPageLoad] = useState<"first" | "last" | null>(null);

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
    } else if (page > 1) {
      // Load previous page and go to last item
      setPendingIndexAfterPageLoad("last");
      setPage(page - 1);
    }
  };

  const handleNext = async () => {
    if (selectedTestCaseIndex < testCases.length - 1) {
      // Navigate within current page
      setSelectedTestCaseIndex(selectedTestCaseIndex + 1);
    } else if (page < totalPages) {
      // Load next page and go to first item
      setPendingIndexAfterPageLoad("first");
      setPage(page + 1);
    }
  };

  // Calculate global index for display
  const globalIndex = (page - 1) * pageSize + selectedTestCaseIndex;

  // Extract unique variable columns and eval columns from test cases
  const variableColumns = React.useMemo(() => {
    const variables = new Set<string>();
    testCases.forEach((tc) => {
      tc.prompt_input_variables.forEach((v) => variables.add(v.variable_name));
    });
    return Array.from(variables);
  }, [testCases]);

  const evalColumns = React.useMemo(() => {
    const evals = new Map<string, { name: string; version: string }>();
    testCases.forEach((tc) => {
      tc.prompt_results.forEach((pr) => {
        pr.evals.forEach((e) => {
          const key = `${e.eval_name}-${e.eval_version}`;
          if (!evals.has(key)) {
            evals.set(key, { name: e.eval_name, version: e.eval_version });
          }
        });
      });
    });
    return Array.from(evals.values());
  }, [testCases]);

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  if (isLoading) {
    return (
      <Box className="flex items-center justify-center p-8">
        <Typography>Loading results...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="flex items-center justify-center p-8">
        <Typography color="error">{error.message}</Typography>
      </Box>
    );
  }

  if (testCases.length === 0) {
    return (
      <Box className="flex items-center justify-center p-8">
        <Typography className="text-gray-600">No test cases found</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <TableContainer component={Paper} elevation={1}>
        <Table aria-label="experiment results table">
          <TableHead>
            <TableRow>
              <TableCell>
                <Box component="span" className="font-semibold">
                  Status
                </Box>
              </TableCell>
              {evalColumns.map((evalCol) => (
                <TableCell key={`${evalCol.name}-${evalCol.version}`}>
                  <Box component="span" className="font-semibold">
                    {evalCol.name} v{evalCol.version}
                  </Box>
                </TableCell>
              ))}
              {variableColumns.map((varName) => (
                <TableCell key={varName}>
                  <Box component="span" className="font-semibold">
                    {varName}
                  </Box>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {testCases.map((testCase, index) => (
              <TestCaseRow
                key={testCase.dataset_row_id || index}
                testCase={testCase}
                variableColumns={variableColumns}
                evalColumns={evalColumns}
                onClick={() => handleRowClick(index)}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {totalPages > 1 && (
        <Box className="flex justify-center mt-4">
          <Pagination
            count={totalPages}
            page={page}
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
