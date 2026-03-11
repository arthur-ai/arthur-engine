import { useAppForm } from "@arthur/shared-components";
import AddIcon from "@mui/icons-material/Add";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import {
  Box,
  Button,
  ButtonGroup,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import z from "zod";

import { createColumns } from "./data/columns";
import { useAgentNotebooks } from "./hooks/useAgentNotebooks";
import { useCreateAgenticNotebook } from "./hooks/useCreateAgenticNotebook";
import { useDeleteAgenticNotebook } from "./hooks/useDeleteAgenticNotebook";

import { getContentHeight } from "@/constants/layout";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { AgenticNotebookSummary } from "@/lib/api-client/api-client";
import { EVENT_NAMES, track } from "@/services/amplitude";

const DEFAULT_DATA: AgenticNotebookSummary[] = [];

interface AgentNotebookProps {
  embedded?: boolean;
  isCreateModalOpen?: boolean;
  onCreateModalOpen?: () => void;
  onCreateModalClose?: () => void;
}

export const AgentNotebook = ({ embedded = false, isCreateModalOpen, onCreateModalOpen, onCreateModalClose }: AgentNotebookProps) => {
  const { id: taskId } = useParams<{ id: string }>();
  const { pagination, props } = useMRTPagination();
  const navigate = useNavigate();
  const { timezone } = useDisplaySettings();
  const columns = useMemo(() => createColumns(timezone), [timezone]);

  const form = useAppForm({
    defaultValues: {
      name: "",
      description: "",
    },
    onSubmit: async ({ value }) => {
      await createAgenticNotebook.mutateAsync(value);
    },
  });
  const [internalDialogOpen, setInternalDialogOpen] = useState(false);
  const dialogOpen = isCreateModalOpen !== undefined ? isCreateModalOpen : internalDialogOpen;
  const { data, isLoading, isRefetching } = useAgentNotebooks({ page: pagination.pageIndex, page_size: pagination.pageSize });

  const createAgenticNotebook = useCreateAgenticNotebook({
    onSuccess: (data) => {
      if (onCreateModalClose) {
        onCreateModalClose();
      } else {
        setInternalDialogOpen(false);
      }
      track(EVENT_NAMES.AGENT_NOTEBOOK_CREATED, { notebook_id: data.id });
      navigate(`/tasks/${taskId}/agentic-notebooks/${data.id}`);
    },
  });

  const deleteAgenticNotebook = useDeleteAgenticNotebook();

  const handleCreateNotebook = () => {
    track(EVENT_NAMES.AGENT_NOTEBOOK_INTENT_CREATE);
    if (onCreateModalOpen) {
      onCreateModalOpen();
    } else {
      setInternalDialogOpen(true);
    }
  };

  const handleCloseCreateNotebook = () => {
    track(EVENT_NAMES.AGENT_NOTEBOOK_INTENT_CANCEL);
    if (onCreateModalClose) {
      onCreateModalClose();
    } else {
      setInternalDialogOpen(false);
    }
  };

  const table = useMaterialReactTable({
    columns,
    data: data?.data ?? DEFAULT_DATA,
    state: { pagination, isLoading, showProgressBars: isRefetching },
    rowCount: data?.total_count ?? 0,
    pageCount: data?.total_pages ?? 0,
    ...props,
    enableStickyHeader: true,
    muiTablePaperProps: {
      elevation: 1,
      sx: {
        borderRadius: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      },
    },
    muiTableContainerProps: {
      sx: {
        flex: 1,
      },
    },
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        navigate(`/tasks/${taskId}/agentic-notebooks/${row.original.id}`);
      },
      sx: {
        cursor: "pointer",
      },
    }),
    enableColumnPinning: true,
    initialState: { columnPinning: { right: ["mrt-row-actions"] } },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActionMenuItems: ({ row }) => [
      <MenuItem
        disabled={!row.original.latest_run_id}
        key="view_run"
        component={Link}
        to={`/tasks/${row.original.task_id}/agent-experiments/${row.original.latest_run_id}`}
      >
        View Latest Run
      </MenuItem>,
      <Divider />,
      <MenuItem key="delete" onClick={() => deleteAgenticNotebook.mutate(row.original.id)}>
        Delete
      </MenuItem>,
    ],
  });

  return (
    <>
      <Stack
        sx={{
          height: embedded ? "100%" : getContentHeight(),
        }}
      >
        {!embedded && (
          <Box
            className="flex flex-col lg:flex-row lg:items-center justify-between gap-4"
            sx={{
              px: 3,
              pt: 3,
              pb: 2,
              borderBottom: 1,
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <div>
              <Typography variant="h5" color="text.primary" fontWeight="bold" mb={0.5}>
                Agentic Notebooks
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Use agentic notebooks to test and optimize agent-based task execution strategies with a reusable configuration.
              </Typography>
            </div>
            <ButtonGroup size="small" variant="contained" disableElevation>
              <Button startIcon={<AddIcon />} onClick={handleCreateNotebook}>
                Notebook
              </Button>
            </ButtonGroup>
          </Box>
        )}
        {!isLoading && (data?.data?.length ?? 0) === 0 ? (
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
            <MenuBookOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
              No notebooks yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Get started by creating your first agent notebook
            </Typography>
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleCreateNotebook} size="large">
              Notebook
            </Button>
          </Box>
        ) : (
          <MaterialReactTable table={table} />
        )}
      </Stack>

      <Dialog open={dialogOpen} onClose={handleCloseCreateNotebook} fullWidth>
        <DialogTitle>New Notebook</DialogTitle>
        <form
          className="contents"
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
        >
          <DialogContent dividers>
            <Stack gap={2}>
              <form.Field name="name" validators={{ onChange: z.string().min(1, "Name is required") }}>
                {(field) => (
                  <TextField
                    label="Name"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    error={field.state.meta.errors.length > 0}
                    helperText={field.state.meta.errors[0]?.message}
                  />
                )}
              </form.Field>
              <form.Field name="description" validators={{ onChange: z.string() }}>
                {(field) => (
                  <TextField label="Description" value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} multiline rows={3} />
                )}
              </form.Field>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => {
                form.reset();
                handleCloseCreateNotebook();
              }}
            >
              Cancel
            </Button>
            <Button type="submit" variant="contained" disableElevation>
              Create
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
};
