import { OnChangeFn, PaginationState, SortingState } from "@tanstack/react-table";
import { MRT_ColumnDef, MRT_RowData, MRT_TableState, useMaterialReactTable } from "material-react-table";

type Opts<TTable extends MRT_RowData> = {
  data: TTable[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: MRT_ColumnDef<NoInfer<TTable>, any>[];
  pagination: { state: PaginationState; onChange: OnChangeFn<PaginationState>; rowCount?: number; pageCount?: number };
  onRowClick?: (row: NoInfer<TTable>) => void;
  onSortingChange?: OnChangeFn<SortingState>;
  state?: Omit<Partial<MRT_TableState<NoInfer<TTable>>>, "pagination">;
};

export const useTable = <TTable extends MRT_RowData>({ data, columns, pagination, onRowClick, onSortingChange, state }: Opts<TTable>) => {
  return useMaterialReactTable({
    data,
    columns,
    layoutMode: "grid",
    enableStickyHeader: true,
    manualPagination: true,
    manualSorting: true,
    enableColumnVirtualization: true,
    enableRowVirtualization: true,
    rowVirtualizerOptions: { estimateSize: () => 55 },
    state: {
      ...state,
      pagination: pagination.state,
      density: "compact",
    },
    rowCount: pagination.rowCount,
    pageCount: pagination.pageCount,
    onPaginationChange: pagination.onChange,
    onSortingChange,
    muiTablePaperProps: {
      variant: "outlined",
      sx: {
        display: "flex",
        flexDirection: "column",
        flex: 1,
      },
    },
    muiTableContainerProps: {
      sx: {
        flex: 1,
      },
    },
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => onRowClick?.(row.original),
    }),
    // Features
    enableDensityToggle: false,
    enableFilters: false,
  });
};
