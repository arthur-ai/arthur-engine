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
  Box,
  Stack,
} from "@mui/material";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo, useRef } from "react";
import { NavigateFunction, useNavigate } from "react-router";

import { Annotation, isContinuousEvalAnnotation } from "./schema";

import { ExpandableTableRow } from "@/components/common";
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
        onNavigate: navigate,
      }),
    [task, navigate]
  );

  const table = useReactTable({
    columns,
    data: annotations,
    getCoreRowModel: getCoreRowModel(),
  });

  const totalColumnSize = table.getAllColumns().reduce((total, column) => total + column.getSize(), 0);

  return (
    <TableContainer ref={container} component={Paper} variant="outlined" sx={{ flexGrow: 0, flexShrink: 1 }}>
      {/* Fixed layout keeps column widths stable when a row's full-width detail panel expands */}
      <Table stickyHeader size="small" sx={{ tableLayout: "fixed" }}>
        <TableHead>
          {table.getHeaderGroups().map((header) => (
            <TableRow key={header.id}>
              <TableCell padding="checkbox" sx={{ width: 48 }} />
              {header.headers.map((header) => (
                <TableCell colSpan={header.colSpan} key={header.id} sx={{ width: `${(header.getSize() / totalColumnSize) * 100}%` }}>
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableHead>
        <TableBody>
          {table.getRowModel().rows.map((row) => (
            <ExpandableTableRow
              key={row.id}
              colSpan={row.getVisibleCells().length + 1}
              expandDisabled={!hasDetail(row.original)}
              detail={<AnnotationDetail annotation={row.original} defaultCurrency={defaultCurrency} />}
            >
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
              ))}
            </ExpandableTableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const hasDetail = (annotation: Annotation) => Boolean(annotation.annotation_description) || isContinuousEvalAnnotation(annotation);

const AnnotationDetail = ({ annotation, defaultCurrency }: { annotation: Annotation; defaultCurrency: string }) => {
  const continuousEval = isContinuousEvalAnnotation(annotation) ? annotation : undefined;

  return (
    <Stack spacing={1.5}>
      <Box>
        <Typography variant="caption" color="text.secondary" component="div">
          Annotation Explanation
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {annotation.annotation_description || "—"}
        </Typography>
      </Box>
      {continuousEval && (
        <Stack direction="row" spacing={4}>
          {continuousEval.eval_name && (
            <Box>
              <Typography variant="caption" color="text.secondary" component="div">
                Eval Name
              </Typography>
              <Typography variant="body2">
                {continuousEval.eval_name} {continuousEval.eval_version != null && `(v${continuousEval.eval_version})`}
              </Typography>
            </Box>
          )}
          <Box>
            <Typography variant="caption" color="text.secondary" component="div">
              Cost
            </Typography>
            <Typography variant="body2">
              {continuousEval.eval_type === "ml_eval" ? "N/A" : formatCurrency(continuousEval.cost ?? 0, defaultCurrency)}
            </Typography>
          </Box>
        </Stack>
      )}
    </Stack>
  );
};

const columnHelper = createColumnHelper<Annotation>();

const createColumns = ({
  taskId,
  container,
  onNavigate,
}: {
  taskId: string;
  container: React.RefObject<HTMLDivElement | null>;
  onNavigate: NavigateFunction;
}) => [
  columnHelper.accessor("annotation_type", {
    header: "Annotation Type",
    size: 150,
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
    size: 320,
    cell: ({ row }) => {
      if (!isContinuousEvalAnnotation(row.original)) return null;

      const name = row.original.continuous_eval_name;
      if (!name) return null;

      return <Typography variant="body2">{name}</Typography>;
    },
  }),
  columnHelper.accessor("annotation_score", {
    header: "Annotation Score",
    size: 120,
    cell: ({ getValue }) => getValue(),
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
  columnHelper.display({
    id: "actions",
    size: 130,
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
