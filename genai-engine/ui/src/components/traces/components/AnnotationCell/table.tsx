import LaunchIcon from "@mui/icons-material/Launch";
import { Paper, Table, TableRow, TableCell, TableHead, TableContainer, TableBody, IconButton, Typography } from "@mui/material";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { Annotation } from "./schema";

type Props = {
  annotations: Annotation[];
};

export const AnnotationsTable = ({ annotations }: Props) => {
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
                <TableCell key={header.id}>{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</TableCell>
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

const columns = [
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
  columnHelper.display({
    id: "details",
    cell: ({ row }) => (
      <IconButton onClick={() => console.log(row.original)} size="small">
        <LaunchIcon fontSize="small" />
      </IconButton>
    ),
  }),
];
