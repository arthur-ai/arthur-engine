import AddIcon from "@mui/icons-material/Add";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import { Box, Button, MenuItem, Typography } from "@mui/material";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createColumns } from "../../data/experiments-columns";
import { useAgentExperiments } from "../../hooks/useAgentExperiments";
import { useDeleteAgentExperiment } from "../../hooks/useDeleteAgentExperiment";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { AgenticExperimentSummary } from "@/lib/api-client/api-client";

const DEFAULT_DATA: AgenticExperimentSummary[] = [];

export const Experiments = () => {
  const { defaultCurrency } = useDisplaySettings();
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 25,
  });

  const deleteAgentExperiment = useDeleteAgentExperiment();

  const navigate = useNavigate();

  const { data, isLoading, isRefetching } = useAgentExperiments({ page: pagination.pageIndex, page_size: pagination.pageSize });

  const columns = useMemo(() => createColumns(defaultCurrency), [defaultCurrency]);

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

  if (!isLoading && (data?.data?.length ?? 0) === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          textAlign: "center",
          py: 8,
        }}
      >
        <ScienceOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
          No experiments yet
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Get started by creating your first agent experiment
        </Typography>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} to="./new" component={Link} size="large">
          Experiment
        </Button>
      </Box>
    );
  }

  return <MaterialReactTable table={table} />;
};
