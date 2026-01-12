import AddIcon from "@mui/icons-material/Add";
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
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import z from "zod";

import { useAppForm } from "../traces/components/filtering/hooks/form";

import { columns } from "./data/columns";
import { useAgentNotebooks } from "./hooks/useAgentNotebooks";
import { useCreateAgenticNotebook } from "./hooks/useCreateAgenticNotebook";
import { useDeleteAgenticNotebook } from "./hooks/useDeleteAgenticNotebook";

import { getContentHeight } from "@/constants/layout";
import { AgenticNotebookSummary } from "@/lib/api-client/api-client";

const DEFAULT_DATA: AgenticNotebookSummary[] = [];

export const AgentNotebook = () => {
  const navigate = useNavigate();

  const form = useAppForm({
    defaultValues: {
      name: "",
      description: "",
    },
    onSubmit: async ({ value }) => {
      await createAgenticNotebook.mutateAsync(value);
    },
  });
  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const { data, isLoading, isRefetching } = useAgentNotebooks();

  const createAgenticNotebook = useCreateAgenticNotebook({
    onSuccess: (data) => {
      setNewDialogOpen(false);
      navigate(`./${data.id}`);
    },
  });

  const deleteAgenticNotebook = useDeleteAgenticNotebook();

  const table = useMaterialReactTable({
    columns,
    data: data?.data ?? DEFAULT_DATA,
    state: { isLoading, showProgressBars: isRefetching },
    rowCount: data?.total_count ?? 0,
    pageCount: data?.total_pages ?? 0,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        navigate(`./${row.original.id}`);
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
      <MenuItem key="view_run" component={Link} to={`/tasks/${row.original.task_id}/agent-experiments/${row.original.latest_run_id}`}>
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
          height: getContentHeight(),
        }}
      >
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
            <Button startIcon={<AddIcon />} onClick={() => setNewDialogOpen(true)}>
              New Notebook
            </Button>
          </ButtonGroup>
        </Box>
        <MaterialReactTable table={table} />
      </Stack>

      <Dialog open={newDialogOpen} onClose={() => setNewDialogOpen(false)} fullWidth>
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
                setNewDialogOpen(false);
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
