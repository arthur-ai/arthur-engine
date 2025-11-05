import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import { Button, ButtonGroup, Typography } from "@mui/material";
import { Stack } from "@mui/material";
import { useField } from "@tanstack/react-form";
import { ColumnDef, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo } from "react";

import { withForm } from "../filtering/hooks/form";
import { TracesTable } from "../TracesTable";

import { addToDatasetFormOptions } from "./form/shared";
import { usePreviewTableData } from "./hooks/usePreviewTableData";

export const PreviewTable = withForm({
  ...addToDatasetFormOptions,
  render: function Render({ form }) {
    const field = useField({ form, name: "columns" as const });

    const hasData = useMemo(() => field.state.value.some((entry) => !!entry.value), [field.state.value]);

    const { table } = usePreviewTableData(field.state.value);

    if (!hasData) return null;

    return (
      <Stack sx={{ mt: "auto", backgroundColor: "grey.100", px: 4, py: 2 }} gap={1}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.primary" fontWeight="medium">
            Preview: 1 row will be added
          </Typography>
          <ButtonGroup size="small">
            <Button variant="outlined" color="primary" startIcon={<CloseIcon />}>
              Cancel
            </Button>
            <Button variant="contained" color="primary" startIcon={<AddIcon />} type="submit">
              Add Row
            </Button>
          </ButtonGroup>
        </Stack>
        <TracesTable table={table} loading={false} />
      </Stack>
    );
  },
});
