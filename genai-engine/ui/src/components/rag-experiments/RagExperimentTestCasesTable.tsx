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
  Pagination,
  LinearProgress,
  CircularProgress,
} from "@mui/material";
import React, { useMemo, useState, useCallback, useEffect } from "react";

import { RagTestCaseDetailModal } from "./RagTestCaseDetailModal";
import { getRagConfigDisplayName, type RagConfig } from "./utils";

import { useRagExperimentTestCases } from "@/hooks/useRagExperiments";
import type {
  RagTestCase,
  RagEvalResultSummaries,
  TestCaseStatus,
} from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

interface RagExperimentTestCasesTableProps {
  experimentId: string;
  experimentStatus: string;
  ragConfigs: RagConfig[];
  ragEvalSummaries: RagEvalResultSummaries[];
  datasetId: string;
  datasetVersion: number;
}

interface RagConfigEvalColumn {
  ragConfigKey: string;
  ragConfigDisplayName: string;
  evalName: string;
  evalVersion: string;
}

interface EvalGroup {
  evalName: string;
  evalVersion: string;
  ragConfigKeys: string[];
}

const getStatusColor = (status: TestCaseStatus): "default" | "primary" | "info" | "success" | "error" => {
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

interface TestCaseRowProps {
  testCase: RagTestCase;
  columns: RagConfigEvalColumn[];
  evalGroups: EvalGroup[];
  onClick: () => void;
}

const TestCaseRow: React.FC<TestCaseRowProps> = ({
  testCase,
  columns,
  evalGroups,
  onClick,
}) => {
  return (
    <TableRow hover onClick={onClick} sx={{ cursor: "pointer" }}>
      <TableCell>
        <Chip
          label={testCase.status.charAt(0).toUpperCase() + testCase.status.slice(1)}
          size="small"
          sx={getStatusChipSx(getStatusColor(testCase.status))}
        />
      </TableCell>

      {columns.map((column, index) => {
        const ragResult = testCase.rag_results.find((r) => r.rag_config_key === column.ragConfigKey);
        const evalResult = ragResult?.evals.find(
          (e) => e.eval_name === column.evalName && e.eval_version === column.evalVersion
        );

        const score = evalResult?.eval_results?.score;
        const isPending = !evalResult?.eval_results;

        // Check if this is the last eval in its RAG config group
        const isLastInGroup =
          index === columns.length - 1 || columns[index + 1].ragConfigKey !== column.ragConfigKey;

        return (
          <TableCell
            key={`${column.ragConfigKey}-${column.evalName}-${column.evalVersion}`}
            align="center"
            sx={{
              padding: "6px 8px",
              borderRight: isLastInGroup ? (index === columns.length - 1 ? 3 : 0) : 0,
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

        evalGroup.ragConfigKeys.forEach((ragConfigKey) => {
          const ragResult = testCase.rag_results.find((r) => r.rag_config_key === ragConfigKey);
          const evalResult = ragResult?.evals.find(
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

export const RagExperimentTestCasesTable: React.FC<RagExperimentTestCasesTableProps> = ({
  experimentId,
  experimentStatus,
  ragConfigs,
  ragEvalSummaries,
  datasetId,
  datasetVersion,
}) => {
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const { testCases, totalPages, totalCount, isLoading, error, isFetching } =
    useRagExperimentTestCases(experimentId, page, pageSize, experimentStatus);

  const [selectedTestCaseIndex, setSelectedTestCaseIndex] = useState<number>(-1);
  const [modalOpen, setModalOpen] = useState(false);
  const [pendingIndexAfterPageLoad, setPendingIndexAfterPageLoad] = useState<"first" | "last" | null>(null);

  // Effect to handle index after page load for keyboard navigation
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

  // Build columns from RAG eval summaries (sorted by performance)
  const { columns, ragConfigGroups, evalGroups } = useMemo(() => {
    const cols: RagConfigEvalColumn[] = [];
    const configGroups = new Map<string, { displayName: string; evalCount: number }>();
    const evalGroupsMap = new Map<string, EvalGroup>();

    // Sort summaries by total passes (best first)
    const sortedSummaries = [...ragEvalSummaries].sort((a, b) => {
      const totalPassesA = a.eval_results.reduce((sum, er) => sum + er.pass_count, 0);
      const totalPassesB = b.eval_results.reduce((sum, er) => sum + er.pass_count, 0);
      return totalPassesB - totalPassesA;
    });

    sortedSummaries.forEach((summary) => {
      const ragConfigKey = summary.rag_config_key || "";
      const displayName = getRagConfigDisplayName(summary, ragConfigs);

      if (!configGroups.has(ragConfigKey)) {
        configGroups.set(ragConfigKey, { displayName, evalCount: 0 });
      }

      summary.eval_results.forEach((evalResult) => {
        cols.push({
          ragConfigKey,
          ragConfigDisplayName: displayName,
          evalName: evalResult.eval_name,
          evalVersion: evalResult.eval_version,
        });

        configGroups.get(ragConfigKey)!.evalCount++;

        // Build eval groups for totals
        const evalKey = `${evalResult.eval_name}-${evalResult.eval_version}`;
        if (!evalGroupsMap.has(evalKey)) {
          evalGroupsMap.set(evalKey, {
            evalName: evalResult.eval_name,
            evalVersion: evalResult.eval_version,
            ragConfigKeys: [],
          });
        }
        const group = evalGroupsMap.get(evalKey)!;
        if (!group.ragConfigKeys.includes(ragConfigKey)) {
          group.ragConfigKeys.push(ragConfigKey);
        }
      });
    });

    return {
      columns: cols,
      ragConfigGroups: configGroups,
      evalGroups: Array.from(evalGroupsMap.values()),
    };
  }, [ragEvalSummaries, ragConfigs]);

  const handleRowClick = useCallback((index: number) => {
    setSelectedTestCaseIndex(index);
    setModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setModalOpen(false);
    setSelectedTestCaseIndex(-1);
  }, []);

  const handlePrevious = useCallback(async () => {
    if (selectedTestCaseIndex > 0) {
      setSelectedTestCaseIndex(selectedTestCaseIndex - 1);
    } else if (page > 0) {
      setPendingIndexAfterPageLoad("last");
      setPage(page - 1);
    }
  }, [selectedTestCaseIndex, page]);

  const handleNext = useCallback(async () => {
    if (selectedTestCaseIndex < testCases.length - 1) {
      setSelectedTestCaseIndex(selectedTestCaseIndex + 1);
    } else if (page < totalPages - 1) {
      setPendingIndexAfterPageLoad("first");
      setPage(page + 1);
    }
  }, [selectedTestCaseIndex, testCases.length, page, totalPages]);

  const handlePageChange = useCallback((_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value - 1);
  }, []);

  // Calculate global index for display
  const globalIndex = page * pageSize + selectedTestCaseIndex;

  // If no summaries yet, show placeholder
  if (ragEvalSummaries.length === 0) {
    return (
      <Box className="p-6 bg-gray-50 border border-gray-200 rounded">
        <Typography variant="body1" className="text-gray-600 italic">
          Test case results will be shown when the experiment finishes executing.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <TableContainer component={Paper} sx={{ flexGrow: 0, flexShrink: 1 }}>
        {(isLoading || isFetching) && <LinearProgress />}
        <Table stickyHeader size="small" aria-label="RAG experiment test cases table">
          <TableHead>
            {/* Top header row: RAG configs and Totals */}
            <TableRow>
              <TableCell
                rowSpan={2}
                sx={{ backgroundColor: "grey.50", borderRight: 1, borderColor: "divider" }}
              >
                <Box component="span" className="font-semibold">
                  Status
                </Box>
              </TableCell>

              {Array.from(ragConfigGroups.entries()).map(([ragConfigKey, group], index) => (
                <TableCell
                  key={ragConfigKey}
                  colSpan={group.evalCount}
                  align="center"
                  sx={{
                    backgroundColor: "grey.50",
                    borderRight: index === ragConfigGroups.size - 1 ? 3 : 1,
                    borderColor: "divider",
                  }}
                >
                  <Box component="span" className="font-semibold text-xs">
                    {group.displayName}
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
              {columns.map((col, index) => {
                const isLastInGroup =
                  index === columns.length - 1 ||
                  columns[index + 1].ragConfigKey !== col.ragConfigKey;

                return (
                  <TableCell
                    key={`${col.ragConfigKey}-${col.evalName}-${col.evalVersion}`}
                    align="center"
                    sx={{
                      backgroundColor: "grey.50",
                      borderRight: isLastInGroup ? (index === columns.length - 1 ? 3 : 1) : 0,
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
                <TableCell
                  colSpan={2 + columns.length + evalGroups.length}
                  align="center"
                >
                  <Typography>Loading test cases...</Typography>
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell
                  colSpan={2 + columns.length + evalGroups.length}
                  align="center"
                >
                  <Typography color="error">{error.message}</Typography>
                </TableCell>
              </TableRow>
            ) : testCases.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={2 + columns.length + evalGroups.length}
                  align="center"
                >
                  <Typography className="text-gray-600">No test cases found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              testCases.map((testCase, index) => (
                <TestCaseRow
                  key={testCase.dataset_row_id || index}
                  testCase={testCase}
                  columns={columns}
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

      <RagTestCaseDetailModal
        testCase={selectedTestCaseIndex >= 0 ? testCases[selectedTestCaseIndex] : null}
        open={modalOpen}
        onClose={handleCloseModal}
        currentIndex={globalIndex}
        totalCount={totalCount}
        onPrevious={handlePrevious}
        onNext={handleNext}
        ragConfigs={ragConfigs}
        datasetId={datasetId}
        datasetVersion={datasetVersion}
      />
    </Box>
  );
};
