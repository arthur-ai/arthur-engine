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

export const PreviewTable = withForm({
  ...addToDatasetFormOptions,
  render: function Render({ form }) {
    const field = useField({ form, name: "columns" as const });

    const hasData = useMemo(() => field.state.value.some((entry) => !!entry.value), [field.state.value]);

    const data = useMemo(
      () => [
        field.state.value.reduce(
          (acc, column) => {
            acc[column.name] = column.value;
            return acc;
          },
          {} as Record<string, string>
        ),
      ],
      [field.state.value]
    );

    const columns = useMemo(
      () =>
        Object.keys(data[0]).map((key) => ({
          header: key,
          accessorKey: key,
          enableSorting: false,
        })) as ColumnDef<Record<string, string>>[],
      [data]
    );

    const table = useReactTable({
      columns,
      data,
      getCoreRowModel: getCoreRowModel(),
    });

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
