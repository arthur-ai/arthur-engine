import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import SaveIcon from "@mui/icons-material/Save";
import { Button, ButtonGroup, Typography } from "@mui/material";
import { Stack } from "@mui/material";
import { useField } from "@tanstack/react-form";
import { useMemo } from "react";

import { withForm } from "../filtering/hooks/form";
import { TracesTable } from "../TracesTable";

import { addToDatasetFormOptions } from "./form/shared";
import { usePatchTransform } from "./hooks/usePatchTransform";
import { usePreviewTableData } from "./hooks/usePreviewTableData";

import { Drawer } from "@/components/common/Drawer";

export const PreviewTable = withForm({
  ...addToDatasetFormOptions,
  props: {} as {
    onSaveTransform: () => void;
  },
  render: function Render({ form, onSaveTransform }) {
    const field = useField({ form, name: "columns" as const });

    const hasData = useMemo(() => field.state.value.some((entry) => !!entry.value), [field.state.value]);

    const { table } = usePreviewTableData(field.state.value);

    const patchTransformMutation = usePatchTransform(field.state.value, {
      onSuccess: (data) => {
        form.setFieldValue("transform", data.id);
      },
    });

    if (!hasData) return null;

    return (
      <Stack sx={{ mt: "auto", backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.100"), px: 4, py: 2 }} gap={1}>
        <Stack direction={{ sm: "column", md: "row" }} alignItems={{ sm: "flex-start", md: "center" }} justifyContent="space-between" gap={1}>
          <Typography variant="body2" color="text.primary" fontWeight="medium">
            Preview: 1 row will be added
          </Typography>
          <Stack direction="row" gap={1}>
            <ButtonGroup size="small">
              <Button variant="outlined" color="primary" startIcon={<SaveIcon />} onClick={onSaveTransform} disabled={!hasData}>
                Save new transform
              </Button>
              <Button
                variant="outlined"
                color="primary"
                onClick={() => patchTransformMutation.mutate(form.state.values.transform)}
                loading={patchTransformMutation.isPending}
                disabled={!hasData}
              >
                Save as existing
              </Button>
            </ButtonGroup>
            <ButtonGroup size="small">
              <Drawer.Close render={<Button variant="outlined" color="primary" startIcon={<CloseIcon />} />}>Cancel</Drawer.Close>
              <Button variant="contained" color="primary" startIcon={<AddIcon />} type="submit">
                Add Row
              </Button>
            </ButtonGroup>
          </Stack>
        </Stack>
        <TracesTable table={table} loading={false} />
      </Stack>
    );
  },
});
