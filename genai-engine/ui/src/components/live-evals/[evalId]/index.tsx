import { Operators, TracesEmptyState } from "@arthur/shared-components";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import {
  Box,
  Chip,
  CircularProgress,
  Dialog,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { Link as MuiLink } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { PaginationState } from "@tanstack/react-table";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Details } from "../components/results/components/details";
import { useContinuousEval } from "../hooks/useContinuousEval";
import { continuousEvalsResultsQueryOptions } from "../hooks/useContinuousEvalsResults";

import { createColumns } from "./columns";

import { CopyableChip } from "@/components/common";
import { getContentHeight } from "@/constants/layout";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useTransform } from "@/hooks/transforms/useTransform";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticAnnotationResponse, ContinuousEvalRunStatus } from "@/lib/api-client/api-client";
import { formatDateInTimezone } from "@/utils/formatters";

const DEFAULT_DATA: AgenticAnnotationResponse[] = [];

const STATUS_OPTIONS: Array<{ label: string; value: ContinuousEvalRunStatus | "" }> = [
  { label: "All", value: "" },
  { label: "Passed", value: "passed" },
  { label: "Failed", value: "failed" },
  { label: "Error", value: "error" },
  { label: "Pending", value: "pending" },
  { label: "Running", value: "running" },
  { label: "Skipped", value: "skipped" },
];

export const LiveEvalDetail = () => {
  const { evalId } = useParams<{ evalId: string }>();

  const { task } = useTask();
  const { defaultCurrency, timezone, use24Hour } = useDisplaySettings();
  const api = useApi()!;

  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 10 });
  const [selectedAnnotationId, setSelectedAnnotationId] = useState("");
  const [statusFilter, setStatusFilter] = useState<ContinuousEvalRunStatus | "">("");

  const filters = [
    { name: "continuous_eval_id", operator: Operators.IN, value: [evalId!] },
    ...(statusFilter ? [{ name: "run_status", operator: Operators.EQUALS, value: statusFilter }] : []),
  ];

  const {
    data: resultsData,
    isLoading,
    isFetching,
  } = useQuery({
    ...continuousEvalsResultsQueryOptions({
      api,
      taskId: task?.id ?? "",
      pagination: { page: pagination.pageIndex, page_size: pagination.pageSize },
      filters,
    }),
    enabled: !!task?.id && !!evalId,
  });

  const handleStatusChange = (value: ContinuousEvalRunStatus | "") => {
    setStatusFilter(value);
    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
  };

  const { data: liveEval } = useContinuousEval(evalId ?? "");
  const transform = useTransform(liveEval?.transform_id);
  const hasVariableMappings = liveEval?.transform_variable_mapping && liveEval.transform_variable_mapping.length > 0;

  const columns = useMemo(
    () => createColumns({ taskId: task?.id ?? "", defaultCurrency, timezone, use24Hour }),
    [task?.id, defaultCurrency, timezone, use24Hour]
  );

  const table = useMaterialReactTable({
    columns,
    data: resultsData?.annotations ?? DEFAULT_DATA,
    manualPagination: true,
    onPaginationChange: setPagination,
    state: { pagination, isLoading, showProgressBars: isFetching },
    rowCount: resultsData?.count ?? 0,
    enableTopToolbar: false,
    enableColumnActions: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableSorting: false,
    muiTablePaperProps: { elevation: 0, sx: { border: "none" } },
    renderEmptyRowsFallback: () => (
      <Box sx={{ p: 2 }}>
        <TracesEmptyState title="No evaluated traces found" />
      </Box>
    ),
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => setSelectedAnnotationId(row.original.id),
      sx: { cursor: "pointer" },
    }),
  });

  if (!liveEval) {
    return (
      <div className="flex items-center justify-center h-full">
        <CircularProgress />
      </div>
    );
  }

  return (
    <Stack sx={{ height: getContentHeight() }}>
      {/* Header */}
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack direction="row" alignItems="flex-start" gap={2}>
          <IconButton component={Link} to=".." size="small">
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Stack>
            <Stack direction="row" alignItems="center" gap={2}>
              <Typography variant="h5" fontWeight="bold" color="text.primary">
                {liveEval.name}
              </Typography>
              <Chip label={liveEval.enabled ? "Enabled" : "Disabled"} color={liveEval.enabled ? "success" : "default"} size="small" />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {liveEval.description}
            </Typography>
          </Stack>

          <Stack direction="row" alignItems="center" justifyContent="space-between" ml="auto">
            <Stack direction="row" gap={2} alignItems="center">
              <CopyableChip label={evalId ?? liveEval.id} sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />
              <Typography variant="body2" color="text.secondary">
                Created {formatDateInTimezone(liveEval.created_at, timezone, { hour12: !use24Hour })}
              </Typography>
            </Stack>
          </Stack>
        </Stack>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
        <Stack spacing={3}>
          {/* Configuration Section */}
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Configuration
            </Typography>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Stack gap={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Evaluator
                </Typography>
                <Stack direction="row" alignItems="center" gap={1}>
                  <MuiLink
                    variant="body1"
                    fontWeight={500}
                    component={Link}
                    to={`/tasks/${liveEval.task_id}/evaluators/${encodeURIComponent(liveEval.llm_eval_name ?? "")}/versions/${liveEval.llm_eval_version ?? ""}`}
                  >
                    {liveEval.llm_eval_name}
                  </MuiLink>
                  <Chip label={`v${liveEval.llm_eval_version}`} size="small" sx={{ width: "fit-content" }} />
                </Stack>
              </Stack>

              <Stack spacing={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Transform
                </Typography>
                {transform.isLoading ? (
                  <Skeleton variant="text" width={100} height={20} />
                ) : (
                  <MuiLink variant="body1" fontWeight={500} component={Link} to={`/tasks/${liveEval.task_id}/transforms?id=${transform.data?.id}`}>
                    {transform.data?.name}
                  </MuiLink>
                )}
              </Stack>
            </div>

            {/* Variable Mappings */}
            {hasVariableMappings && (
              <>
                <Divider sx={{ my: 3 }} />
                <Stack gap={2}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    Variable Mappings
                  </Typography>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Eval Variable</TableCell>
                        <TableCell sx={{ width: 40 }} />
                        <TableCell sx={{ fontWeight: 600 }}>Transform Variable</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {liveEval.transform_variable_mapping?.map((mapping) => (
                        <TableRow key={mapping.eval_variable}>
                          <TableCell>
                            <Chip label={mapping.eval_variable} size="small" variant="outlined" sx={{ fontFamily: "monospace" }} />
                          </TableCell>
                          <TableCell sx={{ textAlign: "center" }}>
                            <ArrowForwardIcon fontSize="small" color="action" />
                          </TableCell>
                          <TableCell>
                            <Chip label={mapping.transform_variable} size="small" variant="outlined" sx={{ fontFamily: "monospace" }} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Stack>
              </>
            )}
          </Paper>

          {/* Evaluated Traces */}
          <Paper variant="outlined" sx={{ overflow: "hidden" }}>
            <Box sx={{ px: 3, py: 2, borderBottom: 1, borderColor: "divider" }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Stack>
                  <Typography variant="h6" fontWeight={600}>
                    Evaluated Traces
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Real-time evaluation results as traces are processed
                  </Typography>
                </Stack>
                <FormControl size="small" sx={{ minWidth: 140 }}>
                  <InputLabel>Status</InputLabel>
                  <Select value={statusFilter} label="Status" onChange={(e) => handleStatusChange(e.target.value as ContinuousEvalRunStatus | "")}>
                    {STATUS_OPTIONS.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>
            </Box>
            <MaterialReactTable table={table} />
          </Paper>
        </Stack>
      </Box>

      <Dialog open={!!selectedAnnotationId} onClose={() => setSelectedAnnotationId("")} maxWidth="xl" fullWidth>
        <Details annotationId={selectedAnnotationId || undefined} onClose={() => setSelectedAnnotationId("")} onRerunComplete={() => {}} />
      </Dialog>
    </Stack>
  );
};
