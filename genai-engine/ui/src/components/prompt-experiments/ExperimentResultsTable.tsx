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
import React, { useEffect, useState } from "react";
import { useApi } from "@/hooks/useApi";

interface PromptInputVariable {
  variable_name: string;
  value: string;
}

interface EvalInputVariable {
  variable_name: string;
  value: string;
}

interface EvalResults {
  score: number;
  explanation: string;
  cost: number;
}

interface Eval {
  eval_name: string;
  eval_version: string;
  eval_input_variables: EvalInputVariable[];
  eval_results: EvalResults;
}

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface PromptOutput {
  content: string;
  tool_calls: any[];
  cost: string;
}

interface PromptResult {
  name: string;
  version: number;
  rendered_prompt: Message[];
  output: PromptOutput;
  evals: Eval[];
}

interface TestCase {
  status: "queued" | "running" | "evaluating" | "failed" | "completed";
  retries: number;
  dataset_row_id: string;
  prompt_input_variables: PromptInputVariable[];
  prompt_results: PromptResult[];
}

interface TestCasesResponse {
  data: TestCase[];
  page: number;
  page_size: number;
  total_pages: number;
  total_count: number;
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
}

const TestCaseDetailModal: React.FC<TestCaseDetailModalProps> = ({ testCase, open, onClose }) => {
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
          <Typography variant="h6" className="font-semibold text-gray-900">
            Test Case Details
          </Typography>
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
                          {promptResult.rendered_prompt.map((message, msgIndex) => (
                            <MessageDisplay key={msgIndex} message={message} />
                          ))}
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
  const api = useApi();
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pageSize] = useState(20);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const handleRowClick = (testCase: TestCase) => {
    setSelectedTestCase(testCase);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedTestCase(null);
  };

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

  useEffect(() => {
    loadTestCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, taskId, experimentId, api]);

  const loadTestCases = async () => {
    if (!api) return;

    try {
      setLoading(true);
      setError(null);

      // TODO: Replace with actual API call when endpoint is available
      // const response = await api.api.getTestCasesApiV1TasksTaskIdPromptExperimentsExperimentIdTestCasesGet({
      //   taskId,
      //   experimentId,
      //   page,
      //   pageSize,
      // });
      // setTestCases(response.data.data);
      // setTotalPages(response.data.total_pages);

      // Mock data for now
      const mockTestCases: TestCase[] = Array.from({ length: 5 }, (_, i) => ({
        status: ["completed", "completed", "running", "completed", "failed"][i] as TestCase["status"],
        retries: 0,
        dataset_row_id: `row-${i + 1}`,
        prompt_input_variables: [
          { variable_name: "customer_query", value: `Sample customer query ${i + 1}` },
          { variable_name: "tone", value: ["friendly", "professional", "casual"][i % 3] },
          { variable_name: "customer_name", value: `Customer ${i + 1}` },
          { variable_name: "product_name", value: ["Widget Pro", "Gadget Plus", "Tool Master"][i % 3] },
          { variable_name: "issue_type", value: ["Billing", "Technical", "General"][i % 3] },
          { variable_name: "priority", value: ["High", "Medium", "Low"][i % 3] },
          { variable_name: "language", value: ["English", "Spanish", "French"][i % 3] },
          { variable_name: "account_tier", value: ["Premium", "Standard", "Basic"][i % 3] },
          { variable_name: "response_length", value: ["Short", "Medium", "Long"][i % 3] },
        ],
        prompt_results: [
          {
            name: "customer_support_v2",
            version: 1,
            rendered_prompt: [
              {
                role: "system",
                content: `You are an expert SQL developer specializing in PostgreSQL.
Your task is to convert natural language queries into valid PostgreSQL SQL statements.

Do not ask the user for clarifications or schema definitions. When in doubt, assume a
schema that would make sense for the user's query. It's more important to return plausible SQL
than to be completely accurate.

Guidelines:
- Always generate valid PostgreSQL syntax
- Use appropriate data types and functions
- Include proper WHERE clauses, JOINs, and aggregations as needed
- Be conservative with assumptions about table/column names
- If the query is ambiguous, make reasonable assumptions and note them
- Always return a valid SQL statement that can be executed

Return your response in the following JSON format:
{
  "sqlQuery": "SELECT * FROM table_name WHERE condition;",
  "explanation": "Brief explanation of what this query does"
}`,
              },
              {
                role: "user",
                content: `Sample customer query ${i + 1}. Please respond with a ${["friendly", "professional", "casual"][i % 3]} tone.`,
              },
            ],
            output: {
              content: `{
  "sqlQuery": "SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.created_at >= NOW() - INTERVAL '90 days' GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) > 0 ORDER BY total_spent DESC LIMIT 100;",
  "explanation": "This query retrieves the top 100 customers by total spending who have made at least one order in the last 90 days. It includes their user information, total number of orders, and total amount spent, sorted by spending in descending order."
}`,
              tool_calls: [],
              cost: "0.0012",
            },
            evals: [
              {
                eval_name: "test_evaluator",
                eval_version: "1",
                eval_input_variables: [
                  { variable_name: "response", value: "The response content..." },
                ],
                eval_results: {
                  score: Math.random() > 0.2 ? 1 : 0,
                  explanation: "The response is appropriate and maintains the requested tone.",
                  cost: 0.0008,
                },
              },
              {
                eval_name: "sentiment_evaluator",
                eval_version: "1",
                eval_input_variables: [
                  { variable_name: "text", value: "The response content..." },
                ],
                eval_results: {
                  score: Math.random() > 0.15 ? 1 : 0,
                  explanation: "Positive sentiment detected with appropriate emotional tone.",
                  cost: 0.0010,
                },
              },
              {
                eval_name: "accuracy_evaluator",
                eval_version: "1",
                eval_input_variables: [
                  { variable_name: "response", value: "The response content..." },
                  { variable_name: "expected", value: "Expected content..." },
                ],
                eval_results: {
                  score: Math.random() > 0.25 ? 1 : 0,
                  explanation: "Response accurately addresses the customer query with relevant information.",
                  cost: 0.0009,
                },
              },
            ],
          },
          {
            name: "customer_support_v2",
            version: 2,
            rendered_prompt: [
              {
                role: "system",
                content: `You are an expert SQL developer specializing in PostgreSQL with advanced knowledge of query optimization.
Your task is to convert natural language queries into valid PostgreSQL SQL statements.

IMPORTANT RULES:
- Do not ask the user for clarifications or schema definitions
- When in doubt, assume a schema that would make sense for the user's query
- It's more important to return plausible SQL than to be completely accurate
- Prioritize performance and use appropriate indexes where applicable

Guidelines:
- Always generate valid PostgreSQL syntax
- Use appropriate data types and functions
- Include proper WHERE clauses, JOINs, and aggregations as needed
- Be conservative with assumptions about table/column names
- If the query is ambiguous, make reasonable assumptions and note them
- Always return a valid SQL statement that can be executed
- Consider query optimization and performance

Return your response in the following JSON format:
{
  "sqlQuery": "SELECT * FROM table_name WHERE condition;",
  "explanation": "Brief explanation of what this query does",
  "assumptions": "Any assumptions made about schema or data"
}`,
              },
              {
                role: "user",
                content: `Sample customer query ${i + 1}. Please respond with a ${["friendly", "professional", "casual"][i % 3]} tone.`,
              },
            ],
            output: {
              content: `{
  "sqlQuery": "SELECT u.id, u.name, u.email, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent, AVG(o.total_amount) as avg_order_value FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.created_at >= CURRENT_DATE - INTERVAL '90 days' GROUP BY u.id, u.name, u.email HAVING COUNT(o.id) > 0 ORDER BY total_spent DESC LIMIT 100;",
  "explanation": "This optimized query retrieves the top 100 customers by total spending who have made at least one order in the last 90 days. It includes their user information, total number of orders, total amount spent, and average order value, sorted by spending in descending order.",
  "assumptions": "Assumed 'users' table has columns: id, name, email, created_at. Assumed 'orders' table has columns: id, user_id, total_amount. Used LEFT JOIN to include users even if they have no orders, though HAVING clause filters them out."
}`,
              tool_calls: [],
              cost: "0.0015",
            },
            evals: [
              {
                eval_name: "test_evaluator",
                eval_version: "1",
                eval_input_variables: [
                  { variable_name: "response", value: "The response content..." },
                ],
                eval_results: {
                  score: Math.random() > 0.15 ? 1 : 0,
                  explanation: "Excellent response quality with proper tone matching.",
                  cost: 0.0008,
                },
              },
              {
                eval_name: "sentiment_evaluator",
                eval_version: "1",
                eval_input_variables: [
                  { variable_name: "text", value: "The response content..." },
                ],
                eval_results: {
                  score: Math.random() > 0.1 ? 1 : 0,
                  explanation: "Strong positive sentiment with professional tone.",
                  cost: 0.0010,
                },
              },
              {
                eval_name: "accuracy_evaluator",
                eval_version: "1",
                eval_input_variables: [
                  { variable_name: "response", value: "The response content..." },
                  { variable_name: "expected", value: "Expected content..." },
                ],
                eval_results: {
                  score: Math.random() > 0.2 ? 1 : 0,
                  explanation: "Highly accurate response with detailed information addressing the query.",
                  cost: 0.0009,
                },
              },
            ],
          },
        ],
      }));

      setTestCases(mockTestCases);
      setTotalPages(5);
    } catch (err) {
      console.error("Failed to load test cases:", err);
      setError("Failed to load experiment results");
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  if (loading) {
    return (
      <Box className="flex items-center justify-center p-8">
        <Typography>Loading results...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box className="flex items-center justify-center p-8">
        <Typography color="error">{error}</Typography>
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
                onClick={() => handleRowClick(testCase)}
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
        testCase={selectedTestCase}
        open={modalOpen}
        onClose={handleCloseModal}
      />
    </Box>
  );
};
