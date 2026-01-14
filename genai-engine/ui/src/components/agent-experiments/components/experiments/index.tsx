import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createColumns } from "../../data/experiments-columns";
import { useAgentExperiments } from "../../hooks/useAgentExperiments";

import { AgenticExperimentSummary } from "@/lib/api-client/api-client";

const DEFAULT_DATA: AgenticExperimentSummary[] = [];

export const Experiments = () => {
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 25,
  });

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
  });

  return <MaterialReactTable table={table} />;
};
