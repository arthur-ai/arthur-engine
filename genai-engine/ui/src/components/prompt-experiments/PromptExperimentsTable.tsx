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
import { formatUTCTimestamp, formatTimestampDuration, formatCurrency } from "@/utils/formatters";

export interface PromptExperiment {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  finished_at?: string | null;
  status: "queued" | "running" | "evaluating" | "failed" | "completed";
  prompt_name: string;
  total_rows: number;
  total_cost?: string | null;
}

export interface PromptExperimentsApiResponse {
  data: PromptExperiment[];
  page: number;
  page_size: number;
  total_pages: number;
  total_count: number;
}

interface PromptExperimentsTableProps {
  experiments: PromptExperiment[];
  onRowClick: (experiment: PromptExperiment) => void;
  page: number;
  rowsPerPage: number;
  totalCount: number;
  onPageChange: (event: React.MouseEvent<HTMLButtonElement> | null, newPage: number) => void;
  onRowsPerPageChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  loading?: boolean;
}

export const PromptExperimentsTable: React.FC<PromptExperimentsTableProps> = ({
  experiments,
  onRowClick,
  page,
  rowsPerPage,
  totalCount,
  onPageChange,
  onRowsPerPageChange,
  loading = false,
}) => {

  const getStatusColor = (
    status: PromptExperiment["status"]
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

  const getStatusLabel = (status: PromptExperiment["status"]): string => {
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
    <>
      <TableContainer component={Paper} sx={{ flexGrow: 0, flexShrink: 1 }}>
        {loading && <LinearProgress />}
        <Table stickyHeader size="small" aria-label="experiments table">
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
                  Prompt
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
              <TableCell sx={{ backgroundColor: "grey.50" }}>
                <Box component="span" className="font-semibold">
                  Total Cost
                </Box>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {experiments.map((experiment) => (
              <TableRow
                key={experiment.id}
                hover
                onClick={() => onRowClick(experiment)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell component="th" scope="row">
                  <Box className="font-medium">{experiment.name}</Box>
                </TableCell>
                <TableCell>
                  <Box className="text-sm text-gray-600">
                    {experiment.description || "-"}
                  </Box>
                </TableCell>
                <TableCell>{experiment.prompt_name}</TableCell>
                <TableCell>{experiment.total_rows}</TableCell>
                <TableCell>
                  <Box className="flex items-center gap-2">
                    <Chip
                      label={getStatusLabel(experiment.status)}
                      size="small"
                      sx={getStatusChipSx(getStatusColor(experiment.status))}
                    />
                    {(experiment.status === "running" || experiment.status === "queued") && (
                      <CircularProgress size={16} />
                    )}
                  </Box>
                </TableCell>
                <TableCell>{formatUTCTimestamp(experiment.created_at)}</TableCell>
                <TableCell>{formatUTCTimestamp(experiment.finished_at)}</TableCell>
                <TableCell>
                  {experiment.finished_at ? formatTimestampDuration(experiment.created_at, experiment.finished_at) : "-"}
                </TableCell>
                <TableCell>
                  {experiment.total_cost ? formatCurrency(parseFloat(experiment.total_cost)) : "-"}
                </TableCell>
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
