import { Menu } from "@base-ui/react/menu";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import LaunchIcon from "@mui/icons-material/Launch";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import {
  Paper,
  Table,
  TableRow,
  TableCell,
  TableHead,
  TableContainer,
  TableBody,
  Typography,
  Chip,
  Button,
  List,
  ListItemButton,
  ListItemText,
  ListItemIcon,
} from "@mui/material";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo, useRef } from "react";
import { NavigateFunction, useNavigate } from "react-router-dom";

import { Annotation, isContinuousEvalAnnotation } from "./schema";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useTask } from "@/hooks/useTask";
import { formatCurrency } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

type Props = {
  annotations: Annotation[];
};

export const AnnotationsTable = ({ annotations }: Props) => {
  const { task } = useTask();
  const { defaultCurrency } = useDisplaySettings();
  const navigate = useNavigate();
  const container = useRef<HTMLDivElement>(null);

  const columns = useMemo(
    () =>
      createColumns({
        taskId: task!.id,
        container,
        defaultCurrency,
        onNavigate: navigate,
      }),
    [task, defaultCurrency, navigate]
  );

  const table = useReactTable({
    columns,
    data: annotations,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <TableContainer ref={container} component={Paper} variant="outlined" sx={{ flexGrow: 0, flexShrink: 1, overflowX: "auto" }}>
      <Table stickyHeader size="small" sx={{ minWidth: 1270 }}>
        <TableHead>
          {table.getHeaderGroups().map((header) => (
            <TableRow key={header.id}>
              {header.headers.map((header) => (
                <TableCell colSpan={header.colSpan} key={header.id} sx={{ width: header.getSize() }}>
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
                <TableCell key={cell.id} sx={{ width: cell.column.getSize() }}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const columnHelper = createColumnHelper<Annotation>();

const createColumns = ({
  taskId,
  container,
  defaultCurrency,
  onNavigate,
}: {
  taskId: string;
  container: React.RefObject<HTMLDivElement | null>;
  defaultCurrency: string;
  onNavigate: NavigateFunction;
}) => [
  columnHelper.accessor("annotation_type", {
    header: "Annotation Type",
    size: 130,
    cell: ({ getValue }) => {
      const value = getValue();

      const label = value === "human" ? "Human" : "Continuous Eval";

      return (
        <Typography variant="body2" className="capitalize" sx={{ whiteSpace: "nowrap" }}>
          {label}
        </Typography>
      );
    },
  }),
  columnHelper.display({
    id: "continuous_eval_name",
    header: "Continuous Eval Name",
    size: 150,
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return null;

      const name = row.original.continuous_eval_name;
      if (!name) return null;

      return (
        <Typography variant="body2" sx={{ whiteSpace: "nowrap" }}>
          {name}
        </Typography>
      );
    },
  }),
  columnHelper.accessor("eval_name", {
    header: "Eval Name",
    size: 170,
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return null;

      const evalName = row.original.eval_name;
      const evalVersion = row.original.eval_version;

      if (!evalName) return null;

      return (
        <Typography variant="body2" sx={{ whiteSpace: "nowrap" }}>
          {evalName} {evalVersion != null && `(v${evalVersion})`}
        </Typography>
      );
    },
  }),
  columnHelper.accessor("annotation_score", {
    header: "Annotation Score",
    size: 110,
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("annotation_description", {
    header: "Annotation Explanation",
    size: 380,
    minSize: 320,
    cell: ({ getValue }) => {
      const value = getValue();
      const text = value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
      return <div className="max-h-60 overflow-auto whitespace-pre-wrap break-words">{text}</div>;
    },
  }),
  columnHelper.accessor("run_status", {
    header: "Run Status",
    size: 120,
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return;

      const status = row.original.run_status;
      return <Chip label={status} size="small" sx={getStatusChipSx(status)} />;
    },
  }),
  columnHelper.accessor("cost", {
    header: "Cost",
    size: 90,
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return;

      if (row.original.eval_type === "ml_eval") {
        return <span className="text-nowrap">N/A</span>;
      }
      return <span className="text-nowrap">{formatCurrency(row.original.cost ?? 0, defaultCurrency)}</span>;
    },
  }),
  columnHelper.display({
    id: "actions",
    size: 120,
    cell: ({ row }) => {
      const annotation = row.original;

      if (!isContinuousEvalAnnotation(annotation)) return;

      return (
        <Menu.Root>
          <Menu.Trigger render={<Button variant="outlined" size="small" endIcon={<ArrowDropDownIcon />} />}>Result</Menu.Trigger>
          <Menu.Portal keepMounted container={container.current}>
            <Menu.Positioner sideOffset={8} side="bottom" align="center" className="z-10">
              <Menu.Popup
                render={<List component={Paper} dense className="outline-none origin-(--transform-origin) min-w-(--anchor-width) z-1000" />}
              >
                <Menu.Item
                  render={
                    <ListItemButton onClick={() => onNavigate(`/tasks/${taskId}/evaluate?id=${annotation.id}&section=results`)} className="gap-4" />
                  }
                >
                  <ListItemText primary="View Results" />
                  <ListItemIcon sx={{ minWidth: "min-content" }}>
                    <LaunchIcon color="action" fontSize="small" />
                  </ListItemIcon>
                </Menu.Item>
                <Menu.Item
                  render={
                    <ListItemButton
                      disabled={annotation.run_status !== "error"}
                      onClick={() => onNavigate(`/tasks/${taskId}/evaluate?id=${annotation.id}&section=results&action=rerun`)}
                      className="gap-4"
                    />
                  }
                >
                  <ListItemText primary="Rerun Annotation" />
                  <ListItemIcon sx={{ minWidth: "min-content" }}>
                    <RestartAltIcon color="action" fontSize="small" />
                  </ListItemIcon>
                </Menu.Item>
              </Menu.Popup>
            </Menu.Positioner>
          </Menu.Portal>
        </Menu.Root>
      );
    },
  }),
];
