import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import React, { useCallback, useMemo } from "react";

import type { EvalsTableProps } from "../types";

import EvalRowExpansion from "./EvalRowExpansion";

import { formatDate } from "@/utils/formatters";

type SortableColumn = "name" | "created_at" | "latest_version_created_at";

const EvalsTable = ({ evals, sortColumn, sortDirection, onSort, expandedRows, onToggleRow, onExpandToFullScreen }: EvalsTableProps) => {
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
                direction={sortColumn === "latest_version_created_at" ? sortDirection : "asc"}
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
                  <TableCell>{formatDate(evalMetadata.latest_version_created_at)}</TableCell>
                  <TableCell>{evalMetadata.versions}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={4}>
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <EvalRowExpansion eval={evalMetadata} onExpandToFullScreen={() => onExpandToFullScreen(evalMetadata.name)} />
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

export default EvalsTable;
