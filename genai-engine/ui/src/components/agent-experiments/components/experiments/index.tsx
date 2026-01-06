import { useSuspenseQuery } from "@tanstack/react-query";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo } from "react";

import { createColumns } from "../../data/experiments-columns";
import { agentExperimentsQueryOptions } from "../../hooks/useAgentExperiments";

import { useTask } from "@/hooks/useTask";

export const Experiments = () => {
  const { task } = useTask();

  const { data } = useSuspenseQuery(agentExperimentsQueryOptions(task!.id));

  const columns = useMemo(() => createColumns(), []);

  const table = useMaterialReactTable({
    data,
    columns,
    muiTablePaperProps: {
      elevation: 1,
      sx: {
        borderRadius: 0,
      },
    },
  });

  return <MaterialReactTable table={table} />;
};
