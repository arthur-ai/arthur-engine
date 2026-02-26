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
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable, type ColumnDef, type HeaderGroup } from "@tanstack/react-table";
import React, { useMemo, useState, useCallback, useEffect } from "react";

import { RagTestCaseDetailModal } from "./RagTestCaseDetailModal";
import { getRagConfigDisplayName, type RagConfig } from "./utils";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useRagExperimentTestCases } from "@/hooks/useRagExperiments";
import type { RagTestCase, RagEvalResultSummaries } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

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

const columnHelper = createColumnHelper<RagTestCase>();

// Status column definition
const createStatusColumn = (): ColumnDef<RagTestCase> =>
  columnHelper.display({
    id: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.original.status;
      return <Chip label={status} size="small" sx={getStatusChipSx(status)} />;
    },
  });

// Cost column definition
const createCostColumn = (defaultCurrency: string): ColumnDef<RagTestCase> =>
  columnHelper.display({
    id: "cost",
    header: "Cost",
    cell: ({ row }) => {
      const cost = row.original.total_cost;
      return cost ? formatCurrency(parseFloat(cost), defaultCurrency) : "-";
    },
  });

// Helper to create eval cell for a specific RAG config and eval
const createEvalCell = (ragConfigKey: string, evalName: string, evalVersion: string) => {
  return ({ row }: { row: { original: RagTestCase } }) => {
    const ragResult = row.original.rag_results.find((r) => r.rag_config_key === ragConfigKey);
    const evalResult = ragResult?.evals.find((e) => e.eval_name === evalName && e.eval_version === evalVersion);

    const score = evalResult?.eval_results?.score;
    const isPending = !evalResult?.eval_results;

    if (isPending) {
      return <CircularProgress size={16} sx={{ color: "text.secondary" }} />;
    }

    return score === 1 ? (
      <Box
        sx={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: "20px",
          height: "20px",
          color: "text.secondary",
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
          color: "error.main",
          fontWeight: 600,
          fontSize: "0.8rem",
        }}
      >
        ✕
      </Box>
    );
  };
};

// Helper to create total cell for an eval group
const createTotalCell = (evalGroup: EvalGroup) => {
  return ({ row }: { row: { original: RagTestCase } }) => {
    let passCount = 0;
    let totalCount = 0;

    evalGroup.ragConfigKeys.forEach((ragConfigKey) => {
      const ragResult = row.original.rag_results.find((r) => r.rag_config_key === ragConfigKey);
      const evalResult = ragResult?.evals.find((e) => e.eval_name === evalGroup.evalName && e.eval_version === evalGroup.evalVersion);

      if (evalResult?.eval_results) {
        totalCount++;
        if (evalResult.eval_results.score === 1) {
          passCount++;
        }
      }
    });

    return (
      <Typography
        variant="body2"
        sx={{
          fontSize: "0.8rem",
          fontWeight: 500,
          color: passCount === 0 && totalCount > 0 ? "error.main" : "text.secondary",
        }}
      >
        {passCount}/{totalCount}
      </Typography>
    );
  };
};

// Build dynamic columns based on RAG eval summaries
const buildColumns = (
  ragEvalSummaries: RagEvalResultSummaries[],
  ragConfigs: RagConfig[],
  defaultCurrency: string
): {
  columns: ColumnDef<RagTestCase>[];
  evalColumns: RagConfigEvalColumn[];
  ragConfigGroups: Map<string, { displayName: string; evalCount: number }>;
  evalGroups: EvalGroup[];
} => {
  const evalColumns: RagConfigEvalColumn[] = [];
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
      evalColumns.push({
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

  const evalGroups = Array.from(evalGroupsMap.values());

  // Build TanStack Table column definitions
  // Create eval columns for each RAG config
  const dynamicEvalColumns: ColumnDef<RagTestCase>[] = evalColumns.map((col, index) =>
    columnHelper.display({
      id: `eval-${col.ragConfigKey}-${col.evalName}-${col.evalVersion}`,
      header: `${col.evalName} (v${col.evalVersion})`,
      cell: createEvalCell(col.ragConfigKey, col.evalName, col.evalVersion),
      meta: {
        ragConfigKey: col.ragConfigKey,
        evalName: col.evalName,
        evalVersion: col.evalVersion,
        isLastInGroup: index === evalColumns.length - 1 || evalColumns[index + 1].ragConfigKey !== col.ragConfigKey,
        isLastEvalColumn: index === evalColumns.length - 1,
      },
    })
  );

  // Create totals columns
  const totalColumns: ColumnDef<RagTestCase>[] = evalGroups.map((evalGroup, index) =>
    columnHelper.display({
      id: `total-${evalGroup.evalName}-${evalGroup.evalVersion}`,
      header: `${evalGroup.evalName} (v${evalGroup.evalVersion})`,
      cell: createTotalCell(evalGroup),
      meta: {
        isTotal: true,
        isLastTotal: index === evalGroups.length - 1,
      },
    })
  );

  const columns: ColumnDef<RagTestCase>[] = [createStatusColumn(), ...dynamicEvalColumns, ...totalColumns, createCostColumn(defaultCurrency)];

  return {
    columns,
    evalColumns,
    ragConfigGroups: configGroups,
    evalGroups,
  };
};

// Custom table header component to render grouped headers
interface TableHeaderProps {
  headerGroups: HeaderGroup<RagTestCase>[];
  ragConfigGroups: Map<string, { displayName: string; evalCount: number }>;
  evalGroups: EvalGroup[];
}

const TableHeader: React.FC<TableHeaderProps> = ({ headerGroups, ragConfigGroups, evalGroups }) => {
  return (
    <TableHead>
      {/* Top header row: Status, RAG configs, Totals, Cost */}
      <TableRow>
        <TableCell rowSpan={2} sx={{ borderRight: 1, borderColor: "divider" }}>
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
      </TableRow>

      {/* Bottom header row: Evaluators under each RAG config */}
      {headerGroups.map((headerGroup) => (
        <TableRow key={headerGroup.id}>
          {headerGroup.headers
            .filter((header) => {
              // Skip status and cost columns (they have rowSpan=2)
              return header.id !== "status" && header.id !== "cost";
            })
            .map((header) => {
              const meta = header.column.columnDef.meta as
                | {
                    isLastInGroup?: boolean;
                    isLastEvalColumn?: boolean;
                    isTotal?: boolean;
                    isLastTotal?: boolean;
                  }
                | undefined;

              const isEvalColumn = header.id.startsWith("eval-");
              const isTotalColumn = header.id.startsWith("total-");

              let borderRight = 0;
              if (isEvalColumn && meta?.isLastInGroup) {
                borderRight = meta?.isLastEvalColumn ? 3 : 1;
              } else if (isTotalColumn && meta?.isLastTotal) {
                borderRight = 3;
              }

              return (
                <TableCell
                  key={header.id}
                  align="center"
                  sx={{
                    borderRight,
                    borderColor: "divider",
                    fontSize: "0.75rem",
                  }}
                >
                  <Box component="span" className="font-medium">
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </Box>
                </TableCell>
              );
            })}
        </TableRow>
      ))}
    </TableHead>
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
  const { defaultCurrency } = useDisplaySettings();
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const { testCases, totalPages, totalCount, isLoading, error, isFetching } = useRagExperimentTestCases(
    experimentId,
    page,
    pageSize,
    experimentStatus
  );

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

  // Build columns from RAG eval summaries
  const { columns, evalColumns, ragConfigGroups, evalGroups } = useMemo(
    () => buildColumns(ragEvalSummaries, ragConfigs, defaultCurrency),
    [ragEvalSummaries, ragConfigs, defaultCurrency]
  );

  // TanStack Table instance
  const table = useReactTable({
    data: testCases,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const handleRowClick = useCallback((index: number) => {
    setSelectedTestCaseIndex(index);
    setModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setModalOpen(false);
    setSelectedTestCaseIndex(-1);
  }, []);

  const handlePrevious = useCallback(() => {
    if (selectedTestCaseIndex > 0) {
      setSelectedTestCaseIndex(selectedTestCaseIndex - 1);
    } else if (page > 0) {
      setPendingIndexAfterPageLoad("last");
      setPage(page - 1);
    }
  }, [selectedTestCaseIndex, page]);

  const handleNext = useCallback(() => {
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
      <Box className="p-6 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded">
        <Typography variant="body1" className="text-gray-600 dark:text-gray-400 italic">
          Test case results will be shown when the experiment finishes executing.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <TableContainer component={Paper} elevation={1} sx={{ flexGrow: 0, flexShrink: 1 }}>
        {(isLoading || isFetching) && <LinearProgress />}
        <Table stickyHeader size="small" aria-label="RAG experiment test cases table">
          <TableHeader headerGroups={table.getHeaderGroups()} ragConfigGroups={ragConfigGroups} evalGroups={evalGroups} />

          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={2 + evalColumns.length + evalGroups.length} align="center">
                  <Typography>Loading test cases...</Typography>
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={2 + evalColumns.length + evalGroups.length} align="center">
                  <Typography color="error">{error.message}</Typography>
                </TableCell>
              </TableRow>
            ) : testCases.length === 0 ? (
              <TableRow>
                <TableCell colSpan={2 + evalColumns.length + evalGroups.length} align="center">
                  <Typography className="text-gray-600 dark:text-gray-400">No test cases found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row, index) => (
                <TableRow key={row.id} hover onClick={() => handleRowClick(index)} sx={{ cursor: "pointer" }}>
                  {row.getVisibleCells().map((cell) => {
                    const meta = cell.column.columnDef.meta as
                      | {
                          isLastInGroup?: boolean;
                          isLastEvalColumn?: boolean;
                          isTotal?: boolean;
                          isLastTotal?: boolean;
                        }
                      | undefined;

                    const isEvalColumn = cell.column.id.startsWith("eval-");
                    const isTotalColumn = cell.column.id.startsWith("total-");
                    const isCostColumn = cell.column.id === "cost";

                    let borderRight = 0;
                    if (isEvalColumn && meta?.isLastInGroup) {
                      borderRight = meta?.isLastEvalColumn ? 3 : 0;
                    } else if (isTotalColumn && meta?.isLastTotal) {
                      borderRight = 3;
                    }

                    return (
                      <TableCell
                        key={cell.id}
                        align={isCostColumn ? "right" : isEvalColumn || isTotalColumn ? "center" : undefined}
                        sx={{
                          padding: isEvalColumn ? "6px 8px" : undefined,
                          borderRight,
                          borderColor: "divider",
                          backgroundColor: isTotalColumn ? (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.50") : undefined,
                          fontWeight: isTotalColumn ? 500 : undefined,
                          fontSize: isTotalColumn ? "0.8rem" : undefined,
                        }}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    );
                  })}
                </TableRow>
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
