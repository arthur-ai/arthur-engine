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
import { Link } from "react-router-dom";

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
  const container = useRef<HTMLDivElement>(null);

  const columns = useMemo(
    () =>
      createColumns({
        taskId: task!.id,
        container,
        defaultCurrency,
      }),
    [task, defaultCurrency]
  );

  const table = useReactTable({
    columns,
    data: annotations,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <TableContainer ref={container} component={Paper} variant="outlined" sx={{ flexGrow: 0, flexShrink: 1 }}>
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

const createColumns = ({
  taskId,
  container,
  defaultCurrency,
}: {
  taskId: string;
  container: React.RefObject<HTMLDivElement | null>;
  defaultCurrency: string;
}) => [
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

      return <span className="text-nowrap">{formatCurrency(row.original.cost ?? 0, defaultCurrency)}</span>;
    },
  }),
  columnHelper.display({
    id: "actions",
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
                    <ListItemButton component={Link} to={`/tasks/${taskId}/continuous-evals?id=${annotation.id}&tab=results`} className="gap-4" />
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
                      component={Link}
                      to={`/tasks/${taskId}/continuous-evals?id=${annotation.id}&tab=results&action=rerun`}
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
