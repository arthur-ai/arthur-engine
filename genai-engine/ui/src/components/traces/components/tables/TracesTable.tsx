import { SortingState, type OnChangeFn, type PaginationState } from "@tanstack/react-table";
import { MaterialReactTable, type MRT_ColumnDef, type MRT_RowData } from "material-react-table";

import { useTable } from "../../hooks/useTable";

type TracesTableProps<T extends MRT_RowData> = {
  data: T[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: MRT_ColumnDef<T, any>[];
  rowCount: number;
  pagination: {
    pageIndex: number;
    pageSize: number;
  };
  onPaginationChange: OnChangeFn<PaginationState>;
  isLoading: boolean;
  onRowClick?: (row: T) => void;
  sorting?: SortingState;
};

export const TracesTable = <T extends MRT_RowData>({
  data,
  columns,
  rowCount,
  pagination,
  onPaginationChange,
  isLoading,
  onRowClick,
  sorting,
}: TracesTableProps<T>) => {
  const table = useTable<T>({
    data,
    columns,
    pagination: { state: pagination, onChange: onPaginationChange, rowCount },
    onRowClick,
    state: {
      sorting: sorting ?? [],
      isLoading,
    },
  });

  return <MaterialReactTable table={table} />;
};
