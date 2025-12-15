import LaunchIcon from "@mui/icons-material/Launch";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { Paper, Table, TableRow, TableCell, TableHead, TableContainer, TableBody, Typography, Chip, ButtonGroup, Button } from "@mui/material";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { Annotation, isContinuousEvalAnnotation } from "./schema";

import { useTask } from "@/hooks/useTask";
import { formatCurrency } from "@/utils/formatters";

type Props = {
  annotations: Annotation[];
};

export const AnnotationsTable = ({ annotations }: Props) => {
  const { task } = useTask();

  const columns = useMemo(
    () =>
      createColumns({
        taskId: task!.id,
      }),
    [task]
  );

  const table = useReactTable({
    columns,
    data: annotations,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <TableContainer component={Paper} variant="outlined" sx={{ flexGrow: 0, flexShrink: 1 }}>
      <Table stickyHeader size="small">
        <TableHead>
          {table.getHeaderGroups().map((header) => (
            <TableRow key={header.id}>
              {header.headers.map((header) => (
                <TableCell colSpan={header.colSpan} key={header.id}>
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableHead>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const columnHelper = createColumnHelper<Annotation>();

const getStatusChipSx = (status: string) => {
  const colorMap: Record<string, { color: string; borderColor: string }> = {
    pending: { color: "text.secondary", borderColor: "text.secondary" },
    running: { color: "primary.main", borderColor: "primary.main" },
    passed: { color: "success.main", borderColor: "success.main" },
    failed: { color: "error.main", borderColor: "error.main" },
    error: { color: "error.main", borderColor: "error.main" },
    skipped: { color: "warning.main", borderColor: "warning.main" },
  };

  const colors = colorMap[status.toLowerCase()] || { color: "text.secondary", borderColor: "text.secondary" };
  return {
    ...colors,
    backgroundColor: "transparent",
    borderWidth: 1,
    borderStyle: "solid",
  };
};

const createColumns = ({ taskId }: { taskId: string }) => [
  columnHelper.accessor("annotation_type", {
    header: "Annotation Type",
    cell: ({ getValue }) => {
      const value = getValue();

      const label = value === "human" ? "Human" : "Continuous Eval";

      return (
        <Typography variant="body2" className="capitalize">
          {label}
        </Typography>
      );
    },
  }),
  columnHelper.accessor("eval_name", {
    header: "Eval Name",
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return null;

      const evalName = row.original.eval_name;
      const evalVersion = row.original.eval_version;

      if (!evalName) return null;

      return (
        <Typography variant="body2">
          {evalName} {evalVersion != null && `(v${evalVersion})`}
        </Typography>
      );
    },
  }),
  columnHelper.accessor("annotation_score", {
    header: "Annotation Score",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("annotation_description", {
    header: "Annotation Explanation",
    cell: ({ getValue }) => {
      return <div className="max-h-32 overflow-auto">{getValue()}</div>;
    },
  }),
  columnHelper.accessor("run_status", {
    header: "Run Status",
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return;

      const status = row.original.run_status;
      return <Chip label={status} size="small" sx={getStatusChipSx(status)} />;
    },
  }),
  columnHelper.accessor("cost", {
    header: "Cost",
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return;

      return <span className="text-nowrap">{formatCurrency(row.original.cost ?? 0)}</span>;
    },
  }),
  columnHelper.display({
    id: "actions",
    cell: ({ row }) => {
      const annotation = row.original;

      if (!isContinuousEvalAnnotation(annotation)) return;

      return (
        <ButtonGroup>
          <Button
            component={Link}
            to={`/tasks/${taskId}/continuous-evals?id=${annotation.id}&tab=results`}
            size="small"
            startIcon={<LaunchIcon fontSize="small" />}
          >
            View
          </Button>
          <Button
            component={Link}
            to={`/tasks/${taskId}/continuous-evals?id=${annotation.id}&tab=results&action=rerun`}
            size="small"
            startIcon={<RestartAltIcon fontSize="small" />}
            disabled={annotation.run_status === "passed"}
          >
            Rerun
          </Button>
        </ButtonGroup>
      );
    },
  }),
];
