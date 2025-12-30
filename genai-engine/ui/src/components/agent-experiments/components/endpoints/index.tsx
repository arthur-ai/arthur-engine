import { useSuspenseQuery } from "@tanstack/react-query";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo } from "react";

import { createColumns } from "../../data/endpoints-columns";
import { agentExperimentsEndpointsQueryOptions } from "../../hooks/useAgentExperimentsEndpoints";

export const Endpoints = () => {
  const { data } = useSuspenseQuery(agentExperimentsEndpointsQueryOptions());

  const columns = useMemo(() => createColumns(), []);

  const table = useMaterialReactTable({
    columns,
    data,
    // enableDensityToggle: false,
    enableFilters: false,
    enableHiding: false,
    muiTablePaperProps: {
      elevation: 0,
      sx: {
        borderRadius: 0,
      },
    },
    initialState: { density: "compact" },
  });

  return (
    <>
      <MaterialReactTable table={table} />
    </>
  );
};
