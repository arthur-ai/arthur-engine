import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Box,
  Chip,
  TablePagination,
  LinearProgress,
  CircularProgress,
} from "@mui/material";
import React, { useMemo, useState } from "react";

import { formatRagConfigName } from "./utils";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { RagExperimentSummary } from "@/lib/api-client/api-client";
import { formatDateInTimezone, formatTimestampDuration, capitalize } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

interface RagExperimentsTableProps {
  experiments: RagExperimentSummary[];
  onRowClick: (experiment: RagExperimentSummary) => void;
  page: number;
  rowsPerPage: number;
  totalCount: number;
  onPageChange: (event: React.MouseEvent<HTMLButtonElement> | null, newPage: number) => void;
  onRowsPerPageChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  loading?: boolean;
}

export const RagExperimentsTable: React.FC<RagExperimentsTableProps> = ({
  experiments,
  onRowClick,
  page,
  rowsPerPage,
  totalCount,
  onPageChange,
  onRowsPerPageChange,
  loading = false,
}) => {
  const { timezone, use24Hour } = useDisplaySettings();
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const sortedExperiments = useMemo(() => {
    if (!sortColumn) return experiments;
    return [...experiments].sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;
      switch (sortColumn) {
        case "name":
          aVal = a.name.toLowerCase();
          bVal = b.name.toLowerCase();
          break;
        case "status":
          aVal = a.status;
          bVal = b.status;
          break;
        case "created_at":
          aVal = new Date(a.created_at).getTime();
          bVal = new Date(b.created_at).getTime();
          break;
        default:
          return 0;
      }
      if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }, [experiments, sortColumn, sortDirection]);

  return (
    <>
      <TableContainer component={Paper} elevation={1} sx={{ flexGrow: 0, flexShrink: 1 }}>
        {loading && <LinearProgress />}
        <Table stickyHeader size="small" aria-label="RAG experiments table">
          <TableHead>
            <TableRow>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "name"}
                  direction={sortColumn === "name" ? sortDirection : "asc"}
                  onClick={() => handleSort("name")}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Experiment Name
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Description
                </Box>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  RAG Configs
                </Box>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Dataset (Version)
                </Box>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Test Cases
                </Box>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "status"}
                  direction={sortColumn === "status" ? sortDirection : "asc"}
                  onClick={() => handleSort("status")}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Status
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "created_at"}
                  direction={sortColumn === "created_at" ? sortDirection : "asc"}
                  onClick={() => handleSort("created_at")}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Created At
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Finished At
                </Box>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Duration
                </Box>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedExperiments.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} sx={{ textAlign: "center", py: 6, color: "text.secondary" }}>
                  No experiments found.
                </TableCell>
              </TableRow>
            )}
            {sortedExperiments.map((experiment) => (
              <TableRow key={experiment.id} hover onClick={() => onRowClick(experiment)} sx={{ cursor: "pointer" }}>
                <TableCell component="th" scope="row">
                  <Box className="font-medium">{experiment.name}</Box>
                </TableCell>
                <TableCell>
                  <Box className="text-sm text-gray-600">{experiment.description || "-"}</Box>
                </TableCell>
                <TableCell>
                  <Box className="flex flex-wrap gap-1">
                    {experiment.rag_configs.map((config, idx) => (
                      <Chip
                        key={idx}
                        label={formatRagConfigName(config)}
                        size="small"
                        variant="outlined"
                        sx={{
                          backgroundColor: config.type === "saved" ? "primary.50" : "warning.50",
                          borderColor: config.type === "saved" ? "primary.200" : "warning.200",
                        }}
                      />
                    ))}
                  </Box>
                </TableCell>
                <TableCell>
                  {experiment.dataset_name} (v{experiment.dataset_version})
                </TableCell>
                <TableCell>{experiment.total_rows}</TableCell>
                <TableCell>
                  <Box className="flex items-center gap-2">
                    <Chip label={capitalize(experiment.status)} size="small" sx={getStatusChipSx(experiment.status)} />
                    {(experiment.status === "running" || experiment.status === "queued") && <CircularProgress size={16} />}
                  </Box>
                </TableCell>
                <TableCell>{formatDateInTimezone(experiment.created_at, timezone, { hour12: !use24Hour })}</TableCell>
                <TableCell>{formatDateInTimezone(experiment.finished_at, timezone, { hour12: !use24Hour })}</TableCell>
                <TableCell>{experiment.finished_at ? formatTimestampDuration(experiment.created_at, experiment.finished_at) : "-"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={totalCount}
        onPageChange={onPageChange}
        onRowsPerPageChange={onRowsPerPageChange}
        page={page}
        rowsPerPage={rowsPerPage}
        rowsPerPageOptions={[10, 25, 50, 100]}
        sx={{
          overflow: "visible",
        }}
      />
    </>
  );
};
