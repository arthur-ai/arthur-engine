import { MenuItem } from "@mui/material";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createColumns } from "../../data/experiments-columns";
import { useAgentExperiments } from "../../hooks/useAgentExperiments";
import { useDeleteAgentExperiment } from "../../hooks/useDeleteAgentExperiment";

import { AgenticExperimentSummary } from "@/lib/api-client/api-client";

const DEFAULT_DATA: AgenticExperimentSummary[] = [];

export const Experiments = () => {
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 25,
  });

  const deleteAgentExperiment = useDeleteAgentExperiment();

  const navigate = useNavigate();

  const { data, isLoading, isRefetching } = useAgentExperiments({ page: pagination.pageIndex, page_size: pagination.pageSize });

  const columns = useMemo(() => createColumns(), []);

  const table = useMaterialReactTable({
    data: data?.data ?? DEFAULT_DATA,
    columns,
    muiTablePaperProps: {
      elevation: 1,
      sx: {
        borderRadius: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      },
    },
    onPaginationChange: setPagination,
    state: { pagination, isLoading, showProgressBars: isRefetching },
    rowCount: data?.total_count ?? 0,
    pageCount: data?.total_pages ?? 0,
    manualPagination: true,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        navigate(`./${row.original.id}`);
      },
      sx: {
        cursor: "pointer",
      },
    }),
    muiTableContainerProps: {
      sx: {
        flex: 1,
      },
    },
    enableStickyHeader: true,
    enableColumnPinning: true,
    initialState: { columnPinning: { right: ["mrt-row-actions"] } },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActionMenuItems: ({ row }) => [
      <MenuItem key="delete" onClick={() => deleteAgentExperiment.mutate(row.original.id)} disabled={deleteAgentExperiment.isPending}>
        Delete Experiment
      </MenuItem>,
    ],
  });

  return <MaterialReactTable table={table} />;
};
