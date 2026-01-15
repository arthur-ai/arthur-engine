import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
  Chip,
  TablePagination,
  LinearProgress,
  CircularProgress,
} from "@mui/material";
import React from "react";

import { formatRagConfigName } from "./utils";

import type { RagExperimentSummary } from "@/lib/api-client/api-client";
import { formatUTCTimestamp, formatTimestampDuration, capitalize } from "@/utils/formatters";
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
  return (
    <>
      <TableContainer component={Paper} sx={{ flexGrow: 0, flexShrink: 1 }}>
        {loading && <LinearProgress />}
        <Table stickyHeader size="small" aria-label="RAG experiments table">
          <TableHead>
            <TableRow>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Experiment Name
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Description
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  RAG Configs
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Dataset (Version)
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Test Cases
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Status
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Created At
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Finished At
                </Box>
              </TableCell>
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Duration
                </Box>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {experiments.map((experiment) => (
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
                <TableCell>{formatUTCTimestamp(experiment.created_at)}</TableCell>
                <TableCell>{formatUTCTimestamp(experiment.finished_at)}</TableCell>
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
