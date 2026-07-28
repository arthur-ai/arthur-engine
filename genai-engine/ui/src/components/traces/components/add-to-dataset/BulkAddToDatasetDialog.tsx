import { Autocomplete, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Stack, TextField } from "@mui/material";
import { useStore } from "@tanstack/react-form";

import { useAppForm } from "../filtering/hooks/form";

import { Matcher } from "./components/matcher";
import { TransformSelector } from "./components/transform-selector";
import { addToDatasetFormOptions, hasSelectedTransform } from "./form/shared";

import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import { useDatasets } from "@/hooks/useDatasets";
import { useTask } from "@/hooks/useTask";
import { MAX_PAGE_SIZE } from "@/lib/constants";

type BulkAddToDatasetDialogProps = {
  open: boolean;
  traceCount: number;
  isSubmitting?: boolean;
  onClose: () => void;
  onSelect: (selection: { datasetId: string; transformId: string }) => void;
};

export const BulkAddToDatasetDialog = ({ open, traceCount, isSubmitting = false, onClose, onSelect }: BulkAddToDatasetDialogProps) => {
  const { task } = useTask();

  const form = useAppForm({
    ...addToDatasetFormOptions,
    onSubmit: ({ value, formApi }) => {
      // Guard with the same check the Add button uses so an Enter-key submit
      // can't fire a request with an empty dataset id or the MANUAL_TRANSFORM_ID
      // sentinel.
      if (!value.dataset || !hasSelectedTransform(value.transform)) {
        return;
      }
      onSelect({ datasetId: value.dataset, transformId: value.transform });
      // Reset here as well as in handleClose: the submit path closes the dialog
      // via the parent (TraceLevel's finally), bypassing handleClose, so without
      // this the dataset/transform selections would leak into the next open.
      formApi.reset();
    },
  });

  const datasetId = useStore(form.store, (state) => state.values.dataset);
  const transformId = useStore(form.store, (state) => state.values.transform);

  const datasetsQuery = useDatasets(
    task?.id,
    {
      page: 0,
      pageSize: MAX_PAGE_SIZE,
      sortOrder: "asc",
    },
    { enabled: open }
  );

  const { latestVersion } = useDatasetLatestVersion(datasetId);
  const datasetColumns = latestVersion?.column_names ?? [];

  const canSubmit = Boolean(datasetId) && hasSelectedTransform(transformId);

  const handleClose = () => {
    form.reset();
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Add {traceCount} trace{traceCount !== 1 ? "s" : ""} to dataset
      </DialogTitle>
      <DialogContent>
        <form
          className="contents"
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
        >
          <Stack spacing={2} sx={{ mt: 1 }}>
            <DialogContentText>
              Choose a dataset and a transform. The transform runs against every selected trace to extract its row values.
            </DialogContentText>

            <form.Field name="dataset">
              {(field) => (
                <Autocomplete
                  options={datasetsQuery.datasets}
                  value={datasetsQuery.datasets.find((d) => d.id === field.state.value) || null}
                  loading={datasetsQuery.isLoading}
                  disablePortal
                  sx={{ flex: 1 }}
                  renderInput={(params) => <TextField {...params} label="Select Dataset" />}
                  onChange={(_event, value) => {
                    field.handleChange(value?.id ?? "");
                    // Reset transform when the dataset changes. Empty string is the
                    // "no transform" sentinel recognized by hasSelectedTransform().
                    form.setFieldValue("transform", "");
                    form.setFieldValue("columns", []);
                  }}
                  getOptionLabel={(option) => option.name}
                />
              )}
            </form.Field>

            <TransformSelector
              form={form}
              fields={{
                dataset: "dataset",
                transform: "transform",
                columns: "columns",
              }}
              traceId=""
              flatSpans={[]}
              datasetColumns={datasetColumns}
            />

            <Matcher
              form={form}
              fields={{
                dataset: "dataset",
                transform: "transform",
              }}
              datasetColumns={datasetColumns}
            />
          </Stack>
        </form>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="contained" onClick={() => form.handleSubmit()} disabled={!canSubmit || isSubmitting}>
          Add to dataset
        </Button>
      </DialogActions>
    </Dialog>
  );
};
