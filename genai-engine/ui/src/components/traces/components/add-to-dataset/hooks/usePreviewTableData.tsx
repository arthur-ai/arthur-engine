import { getCoreRowModel, LegacyColumnDef, useLegacyTable } from "@tanstack/react-table/legacy";
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

  const tableColumns: LegacyColumnDef<Record<string, string>>[] = useMemo(() => {
    const keys = Object.keys(data?.[0] ?? {});

    return keys.map((key) => ({
      header: key,
      accessorKey: key,
      enableSorting: false,
    }));
  }, [data]);

  const table = useLegacyTable({
    columns: tableColumns,
    data,
    getCoreRowModel: getCoreRowModel(),
  });

  return {
    table,
  };
};
