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
import React, { useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";

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

interface TestCaseResult {
  row_index: number;
  status: "completed" | "running" | "failed" | "queued";
  rendered_prompt: string;
  response: string;
  eval_results: EvalResult[];
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
  testCase: TestCaseResult | null;
  open: boolean;
  onClose: () => void;
}

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps> = ({ testCase, open, onClose }) => {
  if (!testCase) return null;

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
            Test Case {testCase.row_index + 1}
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
                      {(() => {
                        try {
                          const messages = JSON.parse(testCase.rendered_prompt) as Message[];
                          return messages.map((message, msgIndex) => (
                            <MessageDisplay key={msgIndex} message={message} />
                          ));
                        } catch {
                          // If not JSON, display as plain text
                          return (
                            <Box className="p-3 bg-gray-100 border border-gray-300 rounded">
                              <Typography variant="body2" className="whitespace-pre-wrap text-gray-900">
                                {testCase.rendered_prompt}
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
                      {testCase.response ? (
                        <MessageDisplay message={{ role: "assistant", content: testCase.response }} />
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
                {testCase.eval_results.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                      Evaluations:
                    </Typography>
                    <Box className="space-y-2">
                      {testCase.eval_results.map((evalResult, evalIndex) => (
                        <Box key={evalIndex} className="p-3 bg-blue-50 border border-blue-200 rounded">
                          <Box className="flex items-center justify-between mb-2">
                            <Box className="flex items-center gap-2">
                              <Typography variant="body2" className="font-medium text-gray-900">
                                {evalResult.eval_name} v{evalResult.eval_version}
                              </Typography>
                              {evalResult.score !== undefined ? (
                                <>
                                  <Chip
                                    label={evalResult.score === 1 ? "Pass" : "Fail"}
                                    size="small"
                                    sx={getEvalChipSx(evalResult.score === 1)}
                                  />
                                  {evalResult.cost && (
                                    <Chip
                                      label={`Cost: $${evalResult.cost}`}
                                      size="small"
                                      variant="outlined"
                                    />
                                  )}
                                </>
                              ) : (
                                <Chip label="Pending" size="small" sx={getPendingChipSx()} />
                              )}
                            </Box>
                          </Box>
                          {evalResult.explanation && (
                            <Typography variant="body2" className="text-gray-700 mt-1">
                              {evalResult.explanation}
                            </Typography>
                          )}
                        </Box>
                      ))}
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
  const { experimentConfig } = usePromptContext();
  const [selectedTestCase, setSelectedTestCase] = useState<TestCaseResult | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Mock data for now - this will be replaced with actual data from experiment runs
  const mockResults: TestCaseResult[] = [
    {
      row_index: 0,
      status: "completed",
      rendered_prompt: JSON.stringify([
        { role: "system", content: "You are a helpful assistant." },
        { role: "user", content: "What is the capital of France?" },
      ]),
      response: "The capital of France is Paris.",
      eval_results: [
        { eval_name: "correctness", eval_version: "1", score: 1, explanation: "Answer is accurate and correct" },
        { eval_name: "relevance", eval_version: "1", score: 1, explanation: "Response is directly relevant to the question" },
      ],
    },
    {
      row_index: 1,
      status: "completed",
      rendered_prompt: JSON.stringify([
        { role: "system", content: "You are a helpful assistant." },
        { role: "user", content: "What is 2 + 2?" },
      ]),
      response: "2 + 2 equals 4.",
      eval_results: [
        { eval_name: "correctness", eval_version: "1", score: 1, explanation: "Mathematical answer is correct" },
        { eval_name: "relevance", eval_version: "1", score: 0, explanation: "Response is too verbose for a simple math question" },
      ],
    },
    {
      row_index: 2,
      status: "completed",
      rendered_prompt: JSON.stringify([
        { role: "user", content: "Explain quantum physics" },
      ]),
      response: "Quantum physics is the study of matter and energy at the most fundamental level.",
      eval_results: [
        { eval_name: "correctness", eval_version: "1", score: 1, explanation: "Provides a correct high-level explanation" },
        { eval_name: "relevance", eval_version: "1", score: 0, explanation: "Explanation is too brief and lacks depth" },
      ],
    },
    {
      row_index: 3,
      status: "completed",
      rendered_prompt: JSON.stringify([
        { role: "system", content: "You are a helpful assistant." },
        { role: "user", content: "What is the meaning of life?" },
      ]),
      response: "The meaning of life varies for each person and can include finding happiness, making connections, and contributing to society.",
      eval_results: [
        { eval_name: "correctness", eval_version: "1", score: 1, explanation: "Provides a thoughtful and balanced answer" },
        { eval_name: "relevance", eval_version: "1", score: 1, explanation: "Directly addresses the philosophical question asked" },
      ],
    },
    {
      row_index: 4,
      status: "failed",
      rendered_prompt: JSON.stringify([
        { role: "user", content: "Translate 'hello' to Spanish" },
      ]),
      response: "Bonjour",
      eval_results: [
        { eval_name: "correctness", eval_version: "1", score: 0, explanation: "Translation is in French, not Spanish" },
        { eval_name: "relevance", eval_version: "1", score: 0, explanation: "Wrong language provided" },
      ],
    },
  ];

  const evals = experimentConfig?.eval_list || [];

  const handleRowClick = (testCase: TestCaseResult) => {
    setSelectedTestCase(testCase);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedTestCase(null);
  };

  const getStatusColor = (
    status: TestCaseResult["status"]
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

  const getStatusLabel = (status: TestCaseResult["status"]): string => {
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
      <TableContainer
        component={Paper}
        sx={{
          flex: 1,
          overflow: "auto",
          backgroundColor: "#f8f9fa",
          boxShadow: "0 2px 4px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)"
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
                  borderBottom: "2px solid #dee2e6"
                }}
              >
                Dataset Row
              </TableCell>
              <TableCell
                sx={{
                  fontWeight: 600,
                  width: `${100 / (2 + evals.length)}%`,
                  backgroundColor: "#e9ecef",
                  borderBottom: "2px solid #dee2e6"
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
                    borderBottom: "2px solid #dee2e6"
                  }}
                >
                  {evalRef.name} (v{evalRef.version})
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {mockResults.map((result) => (
              <TableRow
                key={result.row_index}
                hover
                onClick={() => handleRowClick(result)}
                sx={{
                  cursor: "pointer",
                  backgroundColor: "#f8f9fa",
                  "&:hover": {
                    backgroundColor: "#e9ecef"
                  }
                }}
              >
                <TableCell sx={{ borderBottom: "1px solid #e9ecef" }}>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {result.row_index + 1}
                  </Typography>
                </TableCell>
                <TableCell sx={{ borderBottom: "1px solid #e9ecef" }}>
                  <Chip
                    label={getStatusLabel(result.status)}
                    size="small"
                    sx={getStatusChipSx(getStatusColor(result.status))}
                  />
                </TableCell>
                {evals.map((evalRef: any) => {
                  const evalResult = result.eval_results.find(
                    (er) => er.eval_name === evalRef.name && er.eval_version === evalRef.version
                  );
                  const score = evalResult?.score;

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
                      ) : (
                        <ClearOutlinedIcon
                          sx={{
                            color: "#ef4444",
                            fontSize: "1.25rem",
                          }}
                        />
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TestCaseDetailModal testCase={selectedTestCase} open={modalOpen} onClose={handleCloseModal} />
    </Box>
  );
};

export default ResultsTable;
