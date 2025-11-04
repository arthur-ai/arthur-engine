import AddIcon from "@mui/icons-material/Add";
import { Alert, Autocomplete, Button, Snackbar, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useMemo } from "react";

import { flattenSpans } from "../../utils/spans";
import { useAppForm } from "../filtering/hooks/form";

import { Configurator } from "./Configurator";
import { addToDatasetFormOptions } from "./form/shared";
import { PreviewTable } from "./PreviewTable";

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

  const form = useAppForm({
    ...addToDatasetFormOptions,
    onSubmit: async ({ value, formApi }) => {
      const { columns, dataset } = value;

      await mutation.mutateAsync({ datasetId: dataset, columns });
      formApi.reset();
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
      snackbar.showSnackbar("Dataset version created successfully", "success");
    },
    onError: () => {
      snackbar.showSnackbar("Failed to create dataset version", "error");
    },
  });

  const datasetId = useStore(form.store, (state) => state.values.dataset);

  const { data: trace } = useTrace(traceId);
  const { datasets } = useDatasets(task?.id, {
    page: 0,
    pageSize: MAX_PAGE_SIZE,
    sortOrder: "asc",
  });
  const selectedDataset = datasets.find((dataset) => datasetId === dataset.id);

  const flatSpans = useMemo(() => flattenSpans(trace?.root_spans ?? []), [trace]);

  return (
    <>
      <Drawer>
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
                    options={datasets}
                    disablePortal
                    renderInput={(params) => <TextField {...params} label="Select Dataset" />}
                    onChange={(event, value) => {
                      field.handleChange(value?.id ?? "");
                    }}
                    getOptionLabel={(option) => option.name}
                  />
                )}
              </form.Field>
              {selectedDataset && <Configurator form={form} dataset={selectedDataset} spans={flatSpans} />}
            </Stack>

            <PreviewTable form={form} />
          </form>

          <Snackbar {...snackbar.snackbarProps}>
            <Alert {...snackbar.alertProps} />
          </Snackbar>
        </Drawer.Content>
      </Drawer>
    </>
  );
};
