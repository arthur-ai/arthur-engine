import { ColumnDef, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo } from "react";
import { Column } from "../form/shared";

export const usePreviewTableData = (columns: Column[]) => {
  const data = useMemo(
    () => [
      columns.reduce(
        (acc, column) => {
          acc[column.name] = column.value;
          return acc;
        },
        {} as Record<string, string>
      ),
    ],
    [columns]
  );

  const tableColumns: ColumnDef<Record<string, string>>[] = useMemo(() => {
    const keys = Object.keys(data?.[0] ?? {});

    return keys.map((key) => ({
      header: key,
      accessorKey: key,
      enableSorting: false,
    }));
  }, [data]);

  const table = useReactTable({
    columns: tableColumns,
    data,
    getCoreRowModel: getCoreRowModel(),
  });

  return {
    table,
  };
};
