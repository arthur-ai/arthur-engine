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
  Collapse,
  Chip,
} from "@mui/material";
import React, { useCallback, useMemo } from "react";

import { EvalRowExpansion } from "./EvalRowExpansion";

import type { LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";

interface EvalsTableProps {
  evals: LLMGetAllMetadataResponse[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  expandedRows: Set<string>;
  onToggleRow: (evalName: string) => void;
  onExpandToFullScreen: (evalName: string) => void;
}

type SortableColumn = "name" | "created_at" | "latest_version_created_at";

export const EvalsTable: React.FC<EvalsTableProps> = ({
  evals,
  sortColumn,
  sortDirection,
  onSort,
  expandedRows,
  onToggleRow,
  onExpandToFullScreen,
}) => {
  const formatDate = useCallback((dateString: string): string => {
    try {
      const date = new Date(dateString);
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

  const handleSort = useCallback(
    (column: SortableColumn) => {
      onSort(column);
    },
    [onSort]
  );

  const handleRowClick = useCallback(
    (evalName: string) => {
      onToggleRow(evalName);
    },
    [onToggleRow]
  );

  const sortedEvals = useMemo(() => {
    if (!sortColumn) return evals;

    return [...evals].sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortColumn) {
        case "name":
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case "created_at":
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case "latest_version_created_at":
          aValue = new Date(a.latest_version_created_at).getTime();
          bValue = new Date(b.latest_version_created_at).getTime();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
      if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }, [evals, sortColumn, sortDirection]);

  return (
    <TableContainer
      component={Paper}
      elevation={1}
      sx={{
        overflow: "auto",
        height: "100%",
      }}
    >
      <Table sx={{ minWidth: 650 }} aria-label="evals table" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>
              <Box component="span" sx={{ fontWeight: 600 }}>
                Name
              </Box>
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
              <TableSortLabel
                active={sortColumn === "latest_version_created_at"}
                direction={
                  sortColumn === "latest_version_created_at" ? sortDirection : "asc"
                }
                onClick={() => handleSort("latest_version_created_at")}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Latest Version Created At
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <Box component="span" sx={{ fontWeight: 600 }}>
                Versions
              </Box>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedEvals.map((evalMetadata) => {
            const isExpanded = expandedRows.has(evalMetadata.name);
            return (
              <React.Fragment key={evalMetadata.name}>
                <TableRow
                  hover
                  onClick={() => handleRowClick(evalMetadata.name)}
                  sx={{
                    cursor: "pointer",
                    "&:hover": {
                      backgroundColor: "action.hover",
                    },
                  }}
                >
                  <TableCell component="th" scope="row">
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Box sx={{ fontWeight: 500 }}>{evalMetadata.name}</Box>
                      {evalMetadata.versions > 0 && (
                        <Chip
                          label={`v${evalMetadata.versions}`}
                          size="small"
                          sx={{
                            height: 20,
                            fontSize: "0.75rem",
                            fontWeight: 500,
                          }}
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>{formatDate(evalMetadata.created_at)}</TableCell>
                  <TableCell>
                    {formatDate(evalMetadata.latest_version_created_at)}
                  </TableCell>
                  <TableCell>{evalMetadata.versions}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell
                    style={{ paddingBottom: 0, paddingTop: 0 }}
                    colSpan={4}
                  >
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <EvalRowExpansion
                        eval={evalMetadata}
                        onExpandToFullScreen={() =>
                          onExpandToFullScreen(evalMetadata.name)
                        }
                      />
                    </Collapse>
                  </TableCell>
                </TableRow>
              </React.Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

