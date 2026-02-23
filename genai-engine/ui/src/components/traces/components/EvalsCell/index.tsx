import LaunchIcon from "@mui/icons-material/Launch";
import SyncIcon from "@mui/icons-material/Sync";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { motion } from "framer-motion";
import { useMemo, useState } from "react";

import { ResultChip } from "@/components/common";
import { cn } from "@/utils/cn";

type Props = {
  traceId: string;
  className?: string;
};

export const EvalsCell = ({ traceId, className }: Props) => {
  const [open, setOpen] = useState(false);
  const theme = useTheme();
  const color = theme.palette.success.main;

  const data = useMockEvalsResults(traceId);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const handleOpen = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    setOpen(true);
  };
  return (
    <>
      <motion.button
        className={cn("rounded-md text-nowrap overflow-hidden cursor-pointer group", className)}
        style={{
          backgroundColor: alpha(color, 0.12),
          border: `1px solid ${alpha(color, 0.4)}`,
          color,
        }}
        animate={{ width: "auto" }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: "spring", bounce: 0, duration: 0.25 }}
        onClick={handleOpen}
      >
        <div className="px-1 flex items-center gap-1">
          <SyncIcon sx={{ fontSize: 12 }} />
          <span>3 of 5 evals</span>
        </div>
      </motion.button>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth onClick={(e) => e.stopPropagation()}>
        <DialogTitle>Continuous Evaluations</DialogTitle>
        <DialogContent>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                {table.getHeaderGroups().map((header) => (
                  <TableRow key={header.id}>
                    {header.headers.map((header) => (
                      <TableCell key={header.id}>
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
        </DialogContent>
      </Dialog>
    </>
  );
};

type MockEvalsResults = {
  traceId: string;
  name: string;
  evaluatedAt: string;
  result: "pass" | "fail" | "error";
  reason: string;
};

const useMockEvalsResults = (traceId: string): MockEvalsResults[] => {
  return useMemo(
    () => [
      {
        traceId,
        name: "isValidSql",
        evaluatedAt: "2021-01-01",
        result: "pass",
        reason: "Reason",
      },
      {
        traceId,
        name: "isValidSql",
        evaluatedAt: "2021-01-02",
        result: "fail",
        reason: "Reason",
      },
      {
        traceId,
        name: "Test Eval 1",
        evaluatedAt: "2021-01-03",
        result: "error",
        reason: "Reason",
      },
      {
        traceId,
        name: "Test Eval 1",
        evaluatedAt: "2021-01-04",
        result: "pass",
        reason: "Reason",
      },
    ],
    [traceId]
  );
};

const columns: ColumnDef<MockEvalsResults>[] = [
  {
    id: "result",
    header: "Result",
    accessorKey: "result",
    cell: ({ row }) => {
      return <ResultChip result={row.original.result} score={null} />;
    },
  },
  {
    id: "name",
    header: "Name",
    accessorKey: "name",
    cell: ({ row }) => {
      return (
        <Typography variant="body2" color="text.secondary">
          {row.original.name}
        </Typography>
      );
    },
  },
  {
    id: "reason",
    header: "Reason",
    accessorKey: "reason",
    cell: ({ row }) => {
      return (
        <Typography variant="body2" color="text.secondary">
          {row.original.reason}
        </Typography>
      );
    },
  },
  {
    id: "traceId",
    header: "Trace ID",
    accessorKey: "traceId",
  },
  {
    id: "actions",
    cell: () => {
      return (
        <IconButton size="small">
          <LaunchIcon fontSize="small" />
        </IconButton>
      );
    },
  },
];
