import { Box, LinearProgress, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel } from "@mui/material";
import { flexRender, Row, type Table as TableType } from "@tanstack/react-table";

type Props<TTable> = {
  table: TableType<TTable>;
  ref?: React.RefObject<HTMLDivElement | null>;
  loading: boolean;
  onScroll?: (event: React.UIEvent<HTMLDivElement>) => void;
  onRowClick?: (row: Row<TTable>) => void;
};

export const TracesTable = <TTable,>({ table, ref, loading, onScroll, onRowClick }: Props<TTable>) => {
  return (
    <TableContainer component={Paper} sx={{ flexGrow: 0, flexShrink: 1 }} ref={ref ?? undefined} onScroll={onScroll}>
      {loading && <LinearProgress />}
      <Table stickyHeader size="small">
        <TableHead>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableCell
                  key={header.id}
                  colSpan={header.colSpan}
                  sx={{
                    backgroundColor: "grey.50",
                  }}
                  sortDirection={header.column.getIsSorted()}
                >
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
          {table.getRowModel().rows.map((row) => (
            <TableRow key={row.id} hover onClick={() => onRowClick?.(row)}>
              {row.getVisibleCells().map((cell) => (
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
