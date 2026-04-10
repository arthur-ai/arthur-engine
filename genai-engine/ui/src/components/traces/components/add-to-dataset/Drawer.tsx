import AddIcon from "@mui/icons-material/Add";
import {
  Autocomplete,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Drawer,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useControlled } from "@mui/material/utils";
import { useStore } from "@tanstack/react-form";
import { AxiosError } from "axios";
import { useSnackbar } from "notistack";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { flattenSpans } from "../../utils/spans";
import { useAppForm } from "../filtering/hooks/form";

import { AddColumnDialog } from "./AddColumnDialog";
import { Matcher } from "./components/matcher";
import { TransformSelector } from "./components/transform-selector";
import { Configurator } from "./Configurator";
import { CreateDatasetModal } from "./CreateDatasetModal";
import { addToDatasetFormOptions, TransformDefinition } from "./form/shared";
import { PreviewTable } from "./PreviewTable";
import { SaveTransformDialog } from "./SaveTransformDialog";

import { useCreateDatasetMutation } from "@/hooks/datasets/useCreateDatasetMutation";
import { useTransforms } from "@/hooks/transforms/useTransforms";
import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import { useDatasets } from "@/hooks/useDatasets";
import { useTask } from "@/hooks/useTask";
import { useTrace } from "@/hooks/useTrace";
import { MAX_PAGE_SIZE } from "@/lib/constants";

type Props = {
  traceId: string;
  open?: boolean;
  defaultOpen?: boolean;
  onClose?: () => void;
};

export const AddToDatasetDrawer = ({ traceId, open: openProp, defaultOpen = false, onClose }: Props) => {
  const api = useApi()!;
  const { task } = useTask();
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const navigate = useNavigate();

  const [open, setOpen] = useControlled({
    controlled: openProp,
    default: defaultOpen,
    name: "AddToDatasetDrawer",
    state: "open",
  });
  const [showSaveTransformDialog, setShowSaveTransformDialog] = useState(false);
  const [, setSavedTransformId] = useState<string | undefined>();
  const [showCreateDatasetDialog, setShowCreateDatasetDialog] = useState(false);
  const [showAddColumnDialog, setShowAddColumnDialog] = useState(false);
  const [pendingColumns, setPendingColumns] = useState<Record<string, string[]>>({});
  const [showExitConfirmDialog, setShowExitConfirmDialog] = useState(false);

  const form = useAppForm({
    ...addToDatasetFormOptions,
    onSubmit: async ({ value, formApi }) => {
      const { columns, dataset } = value;

      await mutation.mutateAsync({ datasetId: dataset, columns });
      formApi.reset();
      setSavedTransformId(undefined);
    },
  });

  const mutation = useApiMutation({
    mutationFn: async ({ datasetId, columns }: { datasetId: string; columns: { name: string; value: string }[] }) => {
      // If there are pending columns for this dataset, merge them with the submitted columns
      const columnsForDataset = pendingColumns[datasetId] || [];
      const allColumnNames = new Set([...columnsForDataset, ...columns.map((c) => c.name)]);

      // Create the row data with all columns (pending + submitted)
      const rowData = Array.from(allColumnNames).map((columnName) => {
        const submittedColumn = columns.find((c) => c.name === columnName);
        return {
          column_name: columnName,
          column_value: submittedColumn?.value || "",
        };
      });

      return api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(datasetId, {
        rows_to_add: [
          {
            data: rowData,
          },
        ],
        rows_to_delete: [],
        rows_to_update: [],
      });
    },
    onSuccess: (_data, variables) => {
      enqueueSnackbar("Row added", { variant: "success" });
      // Clear pending columns for this dataset
      setPendingColumns((prev) => {
        const updated = { ...prev };
        delete updated[variables.datasetId];
        return updated;
      });
      setOpen(false);
    },
    onError: () => {
      enqueueSnackbar("Failed to add row", { variant: "error" });
    },
  });

  const datasetId = useStore(form.store, (state) => state.values.dataset);

  const traceQuery = useTrace(traceId);
  const datasetsQuery = useDatasets(
    task?.id,
    {
      page: 0,
      pageSize: MAX_PAGE_SIZE,
      sortOrder: "asc",
    },
    { enabled: open }
  );

  useEffect(() => {
    if (traceQuery.error) {
      enqueueSnackbar("Failed to fetch trace", { variant: "error" });
    } else if (datasetsQuery.error) {
      enqueueSnackbar("Failed to fetch datasets", { variant: "error" });
    }
  }, [traceQuery.error, datasetsQuery.error, enqueueSnackbar]);

  const selectedDataset = datasetsQuery.datasets.find((dataset) => datasetId === dataset.id);
  const flatSpans = useMemo(() => flattenSpans(traceQuery.data?.root_spans ?? []), [traceQuery.data]);

  const { latestVersion } = useDatasetLatestVersion(selectedDataset?.id);
  const transformsQuery = useTransforms();

  // Get the selected transform ID from form state
  const selectedTransformId = useStore(form.store, (state) => state.values.transform);

  // Get columns from the selected transform
  const selectedTransform = transformsQuery.data?.transforms?.find((t) => t.id === selectedTransformId);
  const transformColumns = selectedTransform?.definition.variables.map((varDef) => varDef.variable_name) || [];

  // Merge dataset columns with transform columns to get union of all columns
  const datasetOnlyColumns = selectedDataset?.id ? pendingColumns[selectedDataset.id] || latestVersion?.column_names || [] : [];

  // Create union of dataset columns and transform columns
  const allColumnNames = new Set([...datasetOnlyColumns, ...transformColumns]);
  const datasetColumns = Array.from(allColumnNames);

  const createDatasetMutation = useCreateDatasetMutation(task?.id, (newDataset) => {
    datasetsQuery.refetch();
    form.setFieldValue("dataset", newDataset.id);
    setShowCreateDatasetDialog(false);
    enqueueSnackbar("Dataset created successfully", {
      variant: "success",
      action: () => (
        <Button size="small" color="inherit" onClick={() => navigate(`/tasks/${task?.id}/datasets/${newDataset.id}`)}>
          View Dataset
        </Button>
      ),
    });
  });

  const handleCreateDataset = async (name: string, description: string) => {
    await createDatasetMutation.mutateAsync({
      name,
      description: description || null,
      metadata: null,
    });
  };

  const handleAddColumn = (columnName: string) => {
    if (!selectedDataset) return;

    const currentColumns = datasetColumns;

    // Check if column already exists
    if (currentColumns.includes(columnName)) {
      enqueueSnackbar("Column already exists", { variant: "error" });
      return;
    }

    // Add column to pending columns
    setPendingColumns((prev) => ({
      ...prev,
      [selectedDataset.id]: [...currentColumns, columnName],
    }));

    // Add empty column to form columns
    const currentFormColumns = form.state.values.columns;
    form.setFieldValue("columns", [
      ...currentFormColumns,
      {
        name: columnName,
        value: "",
        path: "",
        span_name: "",
        attribute_path: "",
      },
    ]);

    setShowAddColumnDialog(false);
    enqueueSnackbar("Column added", { variant: "success" });
  };

  const handleSaveTransform = async (name: string, description: string, definition: TransformDefinition) => {
    if (!task?.id) return;

    try {
      const response = await api.api.createTransformForTaskApiV1TasksTaskIdTracesTransformsPost(task.id, {
        name,
        description: description || null,
        definition,
      });

      setSavedTransformId(response.data.id);
      form.setFieldValue("transform", response.data.id);
      transformsQuery.refetch();

      setTimeout(() => {
        setShowSaveTransformDialog(false);
        enqueueSnackbar("Transform saved", {
          variant: "success",
          action: () => (
            <Button size="small" color="inherit" onClick={() => navigate(`/tasks/${task?.id}/transforms`)}>
              View Transforms
            </Button>
          ),
        });
      }, 100);
    } catch (error: unknown) {
      let errorMessage = "Failed to save transform";

      if (error instanceof AxiosError) {
        if (error.response?.status === 409) {
          errorMessage = `A transform named "${name}" already exists. Please use a different name.`;
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.message) {
          errorMessage = error.message;
        }
      }

      throw new Error(errorMessage);
    }
  };

  const hasInProgressWork = form.state.isDirty || form.state.values.columns.length > 0 || Object.keys(pendingColumns).length > 0;

  const doClose = () => {
    form.reset();
    setPendingColumns({});
    setSavedTransformId(undefined);
    setOpen(false);
    onClose?.();
  };

  const handleClose = () => {
    if (hasInProgressWork) {
      setShowExitConfirmDialog(true);
    } else {
      doClose();
    }
  };

  const handleConfirmExit = () => {
    setShowExitConfirmDialog(false);
    doClose();
  };

  const handleCancelExit = () => {
    setShowExitConfirmDialog(false);
  };

  return (
    <>
      <Drawer open={open} onClose={handleClose} slotProps={{ paper: { sx: { width: "80%" } } }} anchor="right">
        <form
          className="contents"
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
        >
          <Stack
            direction="row"
            spacing={0}
            justifyContent="space-between"
            alignItems="center"
            sx={{
              px: 4,
              py: 2,
              backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.100"),
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            <Stack direction="column" spacing={0}>
              <Typography variant="h5" color="text.primary" fontWeight="bold">
                Add to Dataset
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Select a span and drill down through its keys to extract data. The live preview shows the current value.
              </Typography>
            </Stack>
          </Stack>
          <Stack direction="column" gap={2} sx={{ p: 4, overflow: "auto", flex: 1 }}>
            <Stack direction="row" gap={2}>
              <form.Field name="dataset">
                {(field) => {
                  // Add a special "Create New Dataset" option at the end
                  const CREATE_NEW_OPTION = { id: "__create_new__", name: "+ Create New Dataset" } as const;
                  const datasetOptions = [...datasetsQuery.datasets, CREATE_NEW_OPTION];

                  return (
                    <Autocomplete
                      options={datasetOptions}
                      value={datasetsQuery.datasets.find((d) => d.id === field.state.value) || null}
                      disablePortal
                      sx={{ flex: 1 }}
                      renderInput={(params) => <TextField {...params} label="Select Dataset" />}
                      onChange={(_event, value) => {
                        if (value && "id" in value && value.id === "__create_new__") {
                          setShowCreateDatasetDialog(true);
                        } else {
                          field.handleChange(value?.id ?? "");
                          // Reset transform when dataset changes
                          form.setFieldValue("transform", "");
                          form.setFieldValue("columns", []);
                        }
                      }}
                      getOptionLabel={(option) => option.name}
                      renderOption={(props, option) => {
                        const isCreateNew = "id" in option && option.id === "__create_new__";
                        return (
                          <li {...props} key={option.id} style={isCreateNew ? { fontWeight: 500, color: theme.palette.primary.main } : undefined}>
                            {option.name}
                          </li>
                        );
                      }}
                    />
                  );
                }}
              </form.Field>

              <TransformSelector
                form={form}
                fields={{
                  dataset: "dataset",
                  transform: "transform",
                  columns: "columns",
                }}
                traceId={traceId}
                flatSpans={flatSpans}
              />
            </Stack>

            <Matcher
              form={form}
              fields={{
                dataset: "dataset",
                transform: "transform",
              }}
            />

            {selectedDataset && (
              <>
                {datasetColumns.length > 0 && (
                  <Configurator form={form} dataset={selectedDataset} spans={flatSpans} onAddColumn={() => setShowAddColumnDialog(true)} />
                )}

                {datasetColumns.length === 0 && (
                  <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setShowAddColumnDialog(true)} fullWidth>
                    Add New Column
                  </Button>
                )}
              </>
            )}
          </Stack>

          {selectedDataset && datasetColumns.length > 0 && <PreviewTable form={form} onSaveTransform={() => setShowSaveTransformDialog(true)} />}
        </form>
      </Drawer>

      <Dialog open={showExitConfirmDialog} onClose={handleCancelExit}>
        <DialogTitle>Discard in-progress work?</DialogTitle>
        <DialogContent>
          <DialogContentText>You have unsaved changes in the transform builder. Exiting now will discard all in-progress work.</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelExit} variant="outlined">
            Continue editing
          </Button>
          <Button onClick={handleConfirmExit} variant="contained" color="error">
            Discard and exit
          </Button>
        </DialogActions>
      </Dialog>

      <CreateDatasetModal
        open={showCreateDatasetDialog}
        onClose={() => setShowCreateDatasetDialog(false)}
        onSubmit={handleCreateDataset}
        isLoading={createDatasetMutation.isPending}
      />

      <AddColumnDialog
        open={showAddColumnDialog}
        onClose={() => setShowAddColumnDialog(false)}
        onSubmit={handleAddColumn}
        existingColumns={datasetColumns}
      />

      <SaveTransformDialog
        open={showSaveTransformDialog}
        onClose={() => setShowSaveTransformDialog(false)}
        columns={form.state.values.columns}
        onSave={handleSaveTransform}
      />
    </>
  );
};
