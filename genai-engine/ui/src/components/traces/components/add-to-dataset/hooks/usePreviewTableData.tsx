import { type ColumnDef, useTable } from "@tanstack/react-table";
import { useMemo } from "react";

import { tracesTableFeatures } from "../../TracesTable";
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

  const tableColumns: ColumnDef<typeof tracesTableFeatures, Record<string, string>>[] = useMemo(() => {
    const keys = Object.keys(data?.[0] ?? {});

    return keys.map((key) => ({
      header: key,
      accessorKey: key,
      enableSorting: false,
    }));
  }, [data]);

  const table = useTable({
    features: tracesTableFeatures,
    columns: tableColumns,
    data,
  });

  return {
    table,
  };
};
