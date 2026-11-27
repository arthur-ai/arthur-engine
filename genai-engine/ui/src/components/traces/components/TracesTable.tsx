import { Box, LinearProgress, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel } from "@mui/material";
import {
  columnSizingFeature,
  flexRender,
  rowSortingFeature,
  tableFeatures,
  type Row,
  type RowData,
  type Table as TableType,
} from "@tanstack/react-table";

import { TOUR_IDS } from "@/features/task-tour/selectors";

export const tracesTableFeatures = tableFeatures({ rowSortingFeature, columnSizingFeature });

type Props<TTable extends RowData> = {
  table: TableType<typeof tracesTableFeatures, TTable>;
  ref?: React.RefObject<HTMLDivElement | null>;
  loading: boolean;
  onScroll?: (event: React.UIEvent<HTMLDivElement>) => void;
  onRowClick?: (row: Row<typeof tracesTableFeatures, TTable>) => void;
};

export const TracesTable = <TTable extends RowData>({ table, ref, loading, onScroll, onRowClick }: Props<TTable>) => {
  return (
    <TableContainer component={Paper} elevation={1} sx={{ flexGrow: 0, flexShrink: 1 }} ref={ref ?? undefined} onScroll={onScroll}>
      {loading && <LinearProgress />}
      <Table stickyHeader size="small">
        <TableHead>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableCell key={header.id} colSpan={header.colSpan} sortDirection={header.column.getIsSorted()}>
                  <TableSortLabel
                    disabled={!header.column.getCanSort()}
                    active={header.column.getIsSorted() !== false}
                    direction={header.column.getIsSorted() || undefined}
                    onClick={() => {
                      table.setSorting((prev) => [
                        {
                          id: header.column.id,
                          desc: !(prev?.[0].desc ?? false),
                        },
                      ]);
                    }}
                  >
                    <Box sx={{ width: header.getSize() }}>
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </Box>
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableHead>
        <TableBody>
          {table.getRowModel().rows.map((row, rowIndex) => (
            <TableRow key={row.id} hover onClick={() => onRowClick?.(row)} data-tour-id={rowIndex === 0 ? TOUR_IDS.tracesFirstRow : undefined}>
              {row.getAllCells().map((cell) => (
                <TableCell
                  key={cell.id}
                  sx={{
                    maxWidth: cell.column.getSize(),
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
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
