import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { alpha, Box, IconButton, keyframes, TableCell, TableRow } from "@mui/material";
import React, { useEffect, useRef } from "react";

import { DatasetTableCell } from "./DatasetTableCell";

import { CopyableChip } from "@/components/common/CopyableChip";
import { SourceTraceLink } from "@/components/common/SourceTraceLink";
import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

interface DatasetTableRowProps {
  row: DatasetVersionRowResponse;
  columns: string[];
  onEdit: (row: DatasetVersionRowResponse) => void;
  onDelete: (rowId: string) => void;
  datasetId: string;
  taskId?: string;
  onOpenTrace?: (traceId: string) => void;
  onView?: (rowId: string) => void;
  // One-shot flash used when a deep link lands on this row; the row scrolls itself
  // into view and reports the end of the flash via onHighlightEnd.
  isHighlighted?: boolean;
  onHighlightEnd?: () => void;
}

export const DatasetTableRow: React.FC<DatasetTableRowProps> = React.memo(
  ({ row, columns, onEdit, onDelete, datasetId, taskId, onOpenTrace, onView, isHighlighted, onHighlightEnd }) => {
    const rowRef = useRef<HTMLTableRowElement>(null);

    useEffect(() => {
      if (isHighlighted) {
        rowRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, [isHighlighted]);

    return (
      <TableRow
        hover
        ref={rowRef}
        onAnimationEnd={(e) => {
          // Child animations bubble; only the row's own flash ends the highlight.
          if (isHighlighted && e.target === e.currentTarget) {
            onHighlightEnd?.();
          }
        }}
        sx={
          isHighlighted
            ? (theme) => {
                const flash = keyframes`
                  from { background-color: ${alpha(theme.palette.primary.main, 0.18)}; }
                  to { background-color: transparent; }
                `;
                return { animation: `${flash} 2s ease-out` };
              }
            : undefined
        }
      >
        <TableCell
          sx={{
            position: "sticky",
            left: 0,
            backgroundColor: "background.paper",
            zIndex: 1,
            boxShadow: (theme) => (theme.palette.mode === "dark" ? "2px 0 4px rgba(0, 0, 0, 0.3)" : "2px 0 4px rgba(0, 0, 0, 0.1)"),
          }}
        >
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.25 }}>
            <CopyableChip label={row.id} size="small" sx={{ maxWidth: 120, "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" } }} />
            {row.trace_id && taskId && (
              <SourceTraceLink
                variant="subtle"
                taskId={taskId}
                traceId={row.trace_id}
                onOpen={onOpenTrace ? () => onOpenTrace(row.trace_id!) : undefined}
              />
            )}
          </Box>
        </TableCell>
        {columns.map((column) => {
          const columnData = row.data.find((col) => col.column_name === column);
          const value = columnData?.column_value;

          return <DatasetTableCell key={column} value={value} columnName={column} datasetId={datasetId} />;
        })}
        <TableCell
          sx={{
            textAlign: "center",
            position: "sticky",
            right: 0,
            backgroundColor: "background.paper",
            zIndex: 1,
            boxShadow: (theme) => (theme.palette.mode === "dark" ? "-2px 0 4px rgba(0, 0, 0, 0.3)" : "-2px 0 4px rgba(0, 0, 0, 0.1)"),
          }}
        >
          <Box
            sx={{
              display: "flex",
              gap: 0.5,
              justifyContent: "center",
            }}
          >
            {onView && (
              <IconButton
                size="small"
                aria-label="View row"
                title="View dataset row"
                onClick={(e) => {
                  e.stopPropagation();
                  onView(row.id);
                }}
              >
                <VisibilityIcon fontSize="small" />
              </IconButton>
            )}
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onEdit(row);
              }}
              sx={{ color: "primary.main" }}
            >
              <EditIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(row.id);
              }}
              sx={{ color: "error.main" }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Box>
        </TableCell>
      </TableRow>
    );
  }
);
