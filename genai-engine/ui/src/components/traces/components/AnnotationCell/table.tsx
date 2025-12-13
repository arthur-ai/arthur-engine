import LaunchIcon from "@mui/icons-material/Launch";
import { Paper, Table, TableRow, TableCell, TableHead, TableContainer, TableBody, IconButton, Typography, capitalize } from "@mui/material";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { Annotation, isContinuousEvalAnnotation } from "./schema";

import { useTask } from "@/hooks/useTask";
import { formatCurrency } from "@/utils/formatters";

type Props = {
  annotations: Annotation[];
};

export const AnnotationsTable = ({ annotations }: Props) => {
  const navigate = useNavigate();
  const { task } = useTask();

  const columns = useMemo(
    () =>
      createColumns({
        onView: (annotation) => {
          navigate(`/tasks/${task!.id}/continuous-evals?id=${annotation.id}&tab=results`);
        },
      }),
    [task, navigate]
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

const createColumns = ({ onView }: { onView: (annotation: Extract<Annotation, { annotation_type: "continuous_eval" }>) => void }) => [
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
  columnHelper.accessor("annotation_score", {
    header: "Annotation Score",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("annotation_description", {
    header: "Annotation Description",
  }),
  columnHelper.group({
    header: "Continuous Eval",
    columns: [
      columnHelper.accessor("run_status", {
        header: "Run Status",
        cell: ({ row }) => {
          if (!isContinuousEvalAnnotation(row.original)) return;

          return capitalize(row.original.run_status);
        },
      }),
      columnHelper.accessor("cost", {
        header: "Cost",
        cell: ({ row }) => {
          if (!isContinuousEvalAnnotation(row.original)) return;

          return formatCurrency(row.original.cost ?? 0);
        },
      }),
      columnHelper.display({
        id: "actions",
        cell: ({ row }) => {
          const annotation = row.original;

          if (annotation.annotation_type === "human") return;

          return (
            <IconButton onClick={() => onView(annotation)} size="small">
              <LaunchIcon fontSize="small" />
            </IconButton>
          );
        },
      }),
    ],
  }),
];
