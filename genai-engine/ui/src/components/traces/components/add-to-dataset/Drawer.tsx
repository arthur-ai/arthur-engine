import AddIcon from "@mui/icons-material/Add";
import { Alert, Autocomplete, Button, Snackbar, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect, useMemo, useState } from "react";

import { flattenSpans } from "../../utils/spans";
import { useAppForm } from "../filtering/hooks/form";

import { Configurator } from "./Configurator";
import { addToDatasetFormOptions, TransformDefinition } from "./form/shared";
import { PreviewTable } from "./PreviewTable";
import { SaveTransformDialog } from "./SaveTransformDialog";
import { useTransforms } from "./hooks/useTransforms";
import { executeTransform } from "./utils/transformExecutor";

import { Drawer } from "@/components/common/Drawer";
import { useApi } from "@/hooks/useApi";
import { useApiMutation } from "@/hooks/useApiMutation";
import { useDatasets } from "@/hooks/useDatasets";
import useSnackbar from "@/hooks/useSnackbar";
import { useTask } from "@/hooks/useTask";
import { useTrace } from "@/hooks/useTrace";
import { MAX_PAGE_SIZE } from "@/lib/constants";

type Props = {
  traceId: string;
};

export const AddToDatasetDrawer = ({ traceId }: Props) => {
  const api = useApi()!;
  const { task } = useTask();
  const snackbar = useSnackbar();

  const [open, setOpen] = useState(false);
  const [showSaveTransformDialog, setShowSaveTransformDialog] = useState(false);
  const [savedTransformId, setSavedTransformId] = useState<string | undefined>();

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
      return api.api.createDatasetVersionApiV2DatasetsDatasetIdVersionsPost(datasetId, {
        rows_to_add: [
          {
            data: columns.map((column) => ({
              column_name: column.name,
              column_value: column.value,
            })),
          },
        ],
        rows_to_delete: [],
        rows_to_update: [],
      });
    },
    onSuccess: () => {
      snackbar.showSnackbar("Row added", "success");
      setOpen(false);
    },
    onError: () => {
      snackbar.showSnackbar("Failed to add row", "error");
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
      snackbar.showSnackbar("Failed to fetch trace", "error");
    } else if (datasetsQuery.error) {
      snackbar.showSnackbar("Failed to fetch datasets", "error");
    }
  }, [traceQuery.error, datasetsQuery.error, snackbar]);

  const selectedDataset = datasetsQuery.datasets.find((dataset) => datasetId === dataset.id);
  const flatSpans = useMemo(() => flattenSpans(traceQuery.data?.root_spans ?? []), [traceQuery.data]);

  const transformsQuery = useTransforms(selectedDataset?.id);

  const handleSaveTransform = async (name: string, description: string, definition: TransformDefinition) => {
    if (!selectedDataset) return;

    try {
      const response = await api.api.createTransformApiV2DatasetsDatasetIdTransformsPost(selectedDataset.id, {
        name,
        description: description || null,
        definition: definition as any,
      });

      setSavedTransformId(response.data.id);
      transformsQuery.refetch();
      
      setTimeout(() => {
        setShowSaveTransformDialog(false);
        snackbar.showSnackbar("Transform saved", "success");
      }, 100);
    } catch (error: any) {
      let errorMessage = "Failed to save transform";
      
      if (error.response?.status === 409) {
        errorMessage = `A transform named "${name}" already exists. Please use a different name.`;
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      throw new Error(errorMessage);
    }
  };

  const handleClose = () => {
    form.reset();
    setOpen(false);
  };

  return (
    <>
      <Drawer open={open} onOpenChange={setOpen} onClose={handleClose}>
        <Drawer.Trigger render={<Button startIcon={<AddIcon />} />}>Add to Dataset</Drawer.Trigger>

        <Drawer.Content
          slotProps={{
            paper: {
              sx: {
                width: "80%",
              },
            },
          }}
        >
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
                backgroundColor: "grey.100",
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
              <form.Field name="dataset">
                {(field) => (
                  <Autocomplete
                    options={datasetsQuery.datasets}
                    disablePortal
                    renderInput={(params) => <TextField {...params} label="Select Dataset" />}
                    onChange={(_event, value) => {
                      field.handleChange(value?.id ?? "");
                    }}
                    getOptionLabel={(option) => option.name}
                  />
                )}
              </form.Field>

              {selectedDataset && (
                <form.Field name="transform">
                  {(field) => {
                    const options = [{ id: "manual", name: "Manual Entry" }, ...(transformsQuery.data || [])];

                    return (
                      <Autocomplete
                        options={options}
                        value={options.find((opt) => opt.id === field.state.value) || options[0]}
                        disablePortal
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            label="Transform"
                            helperText={
                              transformsQuery.data?.length === 0
                                ? "No transforms yet. Use Manual Entry and save your first transform."
                                : "Select a saved transform or use Manual Entry"
                            }
                          />
                        )}
                        onChange={(_event, value) => {
                          const transformId = value?.id ?? "manual";
                          field.handleChange(transformId);

                          if (transformId !== "manual") {
                            const selectedTransform = transformsQuery.data?.find((t) => t.id === transformId);
                            if (selectedTransform) {
                              const executedColumns = executeTransform(flatSpans, selectedTransform.definition);
                              if (executedColumns) {
                                form.setFieldValue("columns", executedColumns);
                              }
                            }
                          } else {
                            form.setFieldValue("columns", []);
                          }
                        }}
                        getOptionLabel={(option) => option.name}
                      />
                    );
                  }}
                </form.Field>
              )}

              {selectedDataset && <Configurator form={form} dataset={selectedDataset} spans={flatSpans} />}
            </Stack>

            <PreviewTable form={form} onSaveTransform={() => setShowSaveTransformDialog(true)} />
          </form>
        </Drawer.Content>
      </Drawer>

      <SaveTransformDialog
        open={showSaveTransformDialog}
        onClose={() => setShowSaveTransformDialog(false)}
        columns={form.state.values.columns}
        onSave={handleSaveTransform}
      />

      <Snackbar {...snackbar.snackbarProps}>
        <Alert {...snackbar.alertProps} />
      </Snackbar>
    </>
  );
};
