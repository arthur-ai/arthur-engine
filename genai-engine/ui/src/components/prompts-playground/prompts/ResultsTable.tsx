import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import ClearOutlinedIcon from "@mui/icons-material/ClearOutlined";
import CloseIcon from "@mui/icons-material/Close";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Modal from "@mui/material/Modal";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import React, { useState, useEffect } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { useExperimentTestCases } from "@/hooks/usePromptExperiments";
import type { TestCase } from "@/lib/api-client/api-client";

interface ResultsTableProps {
  promptId: string;
}

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface EvalResult {
  eval_name: string;
  eval_version: string;
  score?: number;
  explanation?: string;
  cost?: string;
}

const MessageDisplay: React.FC<{ message: Message }> = ({ message }) => {
  const roleColors: Record<string, string> = {
    system: "bg-purple-100 border-purple-300",
    user: "bg-blue-100 border-blue-300",
    assistant: "bg-green-100 border-green-300",
  };

  return (
    <Box className={`p-3 border rounded mb-2 ${roleColors[message.role] || "bg-gray-100 border-gray-300"}`}>
      <Typography variant="caption" className="font-medium uppercase text-gray-600 mb-1 block">
        {message.role}
      </Typography>
      <Typography variant="body2" className="whitespace-pre-wrap text-gray-900">
        {message.content}
      </Typography>
    </Box>
  );
};

interface TestCaseDetailModalProps {
  testCase: TestCase | null;
  testCaseIndex: number;
  open: boolean;
  onClose: () => void;
}

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps & { promptKey?: string }> = ({ testCase, testCaseIndex, open, onClose, promptKey }) => {
  if (!testCase) return null;

  // Get the prompt result for this specific prompt using the prompt key
  const promptResult = promptKey
    ? testCase.prompt_results?.find((pr: any) => pr.prompt_key === promptKey)
    : testCase.prompt_results?.[0];

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

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="test-case-modal"
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Box
        sx={{
          width: "90%",
          maxWidth: "1200px",
          maxHeight: "90vh",
          bgcolor: "background.paper",
          borderRadius: 1,
          boxShadow: 24,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Modal Header */}
        <Box
          className="flex items-center justify-between p-4 border-b"
          sx={{ backgroundColor: "#f9fafb" }}
        >
          <Typography variant="h6" className="font-semibold text-gray-900">
            Test Case {testCaseIndex + 1}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Modal Content */}
        <Box sx={{ overflow: "auto", p: 4 }}>
          <Box>
            <Card elevation={0} sx={{ border: "1px solid #e5e7eb", mb: 3 }}>
              <CardContent>
                {/* Messages: Rendered Prompt and Output */}
                <Box className="grid grid-cols-2 gap-4 mb-4">
                  {/* Rendered Prompt Messages */}
                  <Box>
                    <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                      Input Messages:
                    </Typography>
                    <Box className="max-h-96 overflow-auto">
                      {promptResult?.rendered_prompt ? (
                        (() => {
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
                        })()
                      ) : (
                        <Box className="p-3 bg-gray-100 border border-gray-300 rounded">
                          <Typography variant="body2" className="text-gray-500 italic">
                            No input messages available
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  </Box>

                  {/* Output */}
                  <Box>
                    <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                      Output Message:
                    </Typography>
                    <Box className="max-h-96 overflow-auto">
                      {promptResult?.output?.content ? (
                        <MessageDisplay message={{ role: "assistant", content: promptResult.output.content }} />
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
                {promptResult?.evals && promptResult.evals.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                      Evaluations:
                    </Typography>
                    <Box className="space-y-2">
                      {promptResult.evals.map((evalData: any, evalIndex: number) => {
                        const evalResult = evalData.eval_results;
                        return (
                          <Box key={evalIndex} className="p-3 bg-blue-50 border border-blue-200 rounded">
                            <Box className="flex items-center justify-between mb-2">
                              <Box className="flex items-center gap-2">
                                <Typography variant="body2" className="font-medium text-gray-900">
                                  {evalData.eval_name} v{evalData.eval_version}
                                </Typography>
                                {evalResult?.score !== undefined ? (
                                  <>
                                    <Chip
                                      label={evalResult.score === 1 ? "Pass" : "Fail"}
                                      size="small"
                                      sx={getEvalChipSx(evalResult.score === 1)}
                                    />
                                  </>
                                ) : (
                                  <Chip label="Pending" size="small" sx={getPendingChipSx()} />
                                )}
                              </Box>
                            </Box>
                            {evalResult?.explanation && (
                              <Typography variant="body2" className="text-gray-700 mt-1">
                                {evalResult.explanation}
                              </Typography>
                            )}
                          </Box>
                        );
                      })}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Box>
        </Box>
      </Box>
    </Modal>
  );
};

const ResultsTable: React.FC<ResultsTableProps> = ({ promptId }) => {
  const { experimentConfig, runningExperimentId, lastCompletedExperimentId, state } = usePromptContext();
  const [selectedTestCase, setSelectedTestCase] = useState<any | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(0);

  // Find the prompt to get its key for filtering results
  const prompt = state.prompts.find((p) => p.id === promptId);

  // Generate the prompt key using the same logic as toExperimentPromptConfig
  // Saved prompts (not dirty): "saved:{name}:{version}"
  // Unsaved prompts (including dirty saved prompts): "unsaved:{name or id}"
  const promptKey = prompt
    ? prompt.name && prompt.version !== null && prompt.version !== undefined && !prompt.isDirty
      ? `saved:${prompt.name}:${prompt.version}`
      : `unsaved:${prompt.name || prompt.id}`
    : undefined;

  // Use running experiment ID if available, otherwise use last completed
  const experimentIdToShow = runningExperimentId || lastCompletedExperimentId;

  // Fetch test cases from the running or completed experiment
  const { testCases, isLoading, refetch } = useExperimentTestCases(
    experimentIdToShow || undefined,
    0,
    100 // Fetch all results for now
  );

  // Refetch test cases when runningExperimentId or lastCompletedExperimentId changes
  useEffect(() => {
    if (runningExperimentId || lastCompletedExperimentId) {
      refetch();
    }
  }, [runningExperimentId, lastCompletedExperimentId, refetch]);

  // Poll for test case updates while experiment is running
  useEffect(() => {
    if (!runningExperimentId) return;

    const pollInterval = setInterval(() => {
      refetch();
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [runningExperimentId, refetch]);

  const evals = experimentConfig?.eval_list || [];

  const handleRowClick = (testCase: TestCase, index: number) => {
    setSelectedTestCase(testCase);
    setSelectedTestCaseIndex(index);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedTestCase(null);
  };

  const getStatusColor = (
    status: TestCase["status"]
  ): "default" | "primary" | "info" | "success" | "error" => {
    switch (status) {
      case "queued":
        return "default";
      case "running":
        return "primary";
      case "completed":
        return "success";
      case "failed":
        return "error";
      default:
        return "default";
    }
  };

  const getStatusLabel = (status: string): string => {
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
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column", p: 1 }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Results
      </Typography>
      {isLoading ? (
        <Box
          sx={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#f8f9fa",
            borderRadius: 1,
            border: "1px solid #e9ecef",
          }}
        >
          <CircularProgress size={40} />
        </Box>
      ) : testCases.length === 0 ? (
        <Box
          sx={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "#f8f9fa",
            borderRadius: 1,
            border: "1px solid #e9ecef",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            {runningExperimentId
              ? "Experiment is running. Results will appear here..."
              : experimentIdToShow
              ? "No test cases found for this experiment."
              : "Click 'Run' or 'Run All Prompts' to execute the experiment and see results."}
          </Typography>
        </Box>
      ) : (
        <TableContainer
          component={Paper}
          sx={{
            flex: 1,
            overflow: "auto",
            backgroundColor: "#f8f9fa",
            boxShadow: "0 2px 4px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)",
          }}
        >
          <Table stickyHeader size="small" sx={{ tableLayout: "fixed", width: "100%" }}>
            <TableHead>
              <TableRow>
                <TableCell
                  sx={{
                    fontWeight: 600,
                    width: `${100 / (2 + evals.length)}%`,
                    backgroundColor: "#e9ecef",
                    borderBottom: "2px solid #dee2e6",
                  }}
                >
                  Dataset Row
                </TableCell>
                <TableCell
                  sx={{
                    fontWeight: 600,
                    width: `${100 / (2 + evals.length)}%`,
                    backgroundColor: "#e9ecef",
                    borderBottom: "2px solid #dee2e6",
                  }}
                >
                  Status
                </TableCell>
                {evals.map((evalRef: any) => (
                  <TableCell
                    key={`${evalRef.name}-${evalRef.version}`}
                    align="center"
                    sx={{
                      fontWeight: 600,
                      width: `${100 / (2 + evals.length)}%`,
                      padding: "6px 8px",
                      backgroundColor: "#e9ecef",
                      borderBottom: "2px solid #dee2e6",
                    }}
                  >
                    {evalRef.name} (v{evalRef.version})
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {testCases.map((testCase, index) => (
                <TableRow
                  key={testCase.dataset_row_id || index}
                  hover
                  onClick={() => handleRowClick(testCase, index)}
                  sx={{
                    cursor: "pointer",
                    backgroundColor: "#f8f9fa",
                    "&:hover": {
                      backgroundColor: "#e9ecef",
                    },
                  }}
                >
                  <TableCell sx={{ borderBottom: "1px solid #e9ecef" }}>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {index + 1}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ borderBottom: "1px solid #e9ecef" }}>
                    <Chip
                      label={getStatusLabel(testCase.status)}
                      size="small"
                      sx={getStatusChipSx(getStatusColor(testCase.status as "completed" | "running" | "failed" | "queued"))}
                    />
                  </TableCell>
                  {evals.map((evalRef: any) => {
                    // Find the result for THIS specific prompt using the prompt key
                    const promptResult = testCase.prompt_results?.find(
                      (pr: any) => pr.prompt_key === promptKey
                    );
                    // Compare eval version as strings since API returns them as strings
                    const evalResult = promptResult?.evals?.find(
                      (e: any) => e.eval_name === evalRef.name && String(e.eval_version) === String(evalRef.version)
                    );
                    const score = evalResult?.eval_results?.score;

                    return (
                      <TableCell
                        key={`${evalRef.name}-${evalRef.version}`}
                        align="center"
                        sx={{ padding: "6px 8px", borderBottom: "1px solid #e9ecef" }}
                      >
                        {score === 1 ? (
                          <CheckCircleOutlinedIcon
                            sx={{
                              color: "#10b981",
                              fontSize: "1.25rem",
                            }}
                          />
                        ) : score === 0 ? (
                          <ClearOutlinedIcon
                            sx={{
                              color: "#ef4444",
                              fontSize: "1.25rem",
                            }}
                          />
                        ) : score === null || score === undefined ? (
                          <Typography variant="caption" color="text.secondary">
                            -
                          </Typography>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            ?
                          </Typography>
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <TestCaseDetailModal testCase={selectedTestCase} testCaseIndex={selectedTestCaseIndex} open={modalOpen} onClose={handleCloseModal} promptKey={promptKey} />
    </Box>
  );
};

export default ResultsTable;
