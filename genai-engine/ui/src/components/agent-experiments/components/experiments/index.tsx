import { useSuspenseQuery } from "@tanstack/react-query";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { createColumns } from "../../data/experiments-columns";
import { agentExperimentsQueryOptions } from "../../hooks/useAgentExperiments";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

export const Experiments = () => {
  const api = useApi()!;
  const { task } = useTask();
  const navigate = useNavigate();

  const { data } = useSuspenseQuery(agentExperimentsQueryOptions({ taskId: task!.id, api }));
  const columns = useMemo(() => createColumns(), []);

  const table = useMaterialReactTable({
    data: data.data,
    columns,
    muiTablePaperProps: {
      elevation: 1,
      sx: {
        borderRadius: 0,
      },
    },
    pageCount: data.total_pages,
    rowCount: data.total_count,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        navigate(`./${row.original.id}`);
      },
      sx: {
        cursor: "pointer",
      },
    }),
  });

  return <MaterialReactTable table={table} />;
};
