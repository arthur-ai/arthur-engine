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
} from "@mui/material";
import React, { useCallback } from "react";

export interface PromptExperiment {
  id: string;
  name: string;
  description: string;
  created_at: string;
  finished_at: string;
  status: "queued" | "running" | "evaluating" | "failed" | "completed";
  prompt_name: string;
  total_rows: number;
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
}

export const PromptExperimentsTable: React.FC<PromptExperimentsTableProps> = ({
  experiments,
  onRowClick,
}) => {

  const formatDate = useCallback((dateString: string): string => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return dateString;
      }
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return dateString;
    }
  }, []);

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

  return (
    <>
      <TableContainer
        component={Paper}
        elevation={1}
        className="overflow-auto h-full"
      >
        <Table className="min-w-[650px]" aria-label="experiments table" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>
                <Box component="span" className="font-semibold">
                  Experiment Name
                </Box>
              </TableCell>
              <TableCell>
                <Box component="span" className="font-semibold">
                  Status
                </Box>
              </TableCell>
              <TableCell>
                <Box component="span" className="font-semibold">
                  Created At
                </Box>
              </TableCell>
              <TableCell>
                <Box component="span" className="font-semibold">
                  Finished At
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
                className="cursor-pointer hover:bg-gray-50"
              >
                <TableCell component="th" scope="row">
                  <Box className="font-medium">{experiment.name}</Box>
                  {experiment.description && (
                    <Box component="div" className="text-sm text-gray-600 mt-1">
                      {experiment.description}
                    </Box>
                  )}
                  <Box component="div" className="text-xs text-gray-500 mt-1 flex gap-4">
                    <span>Prompt: {experiment.prompt_name}</span>
                    <span>Rows: {experiment.total_rows}</span>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={getStatusLabel(experiment.status)}
                    color={getStatusColor(experiment.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell>{formatDate(experiment.created_at)}</TableCell>
                <TableCell>{formatDate(experiment.finished_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
};
