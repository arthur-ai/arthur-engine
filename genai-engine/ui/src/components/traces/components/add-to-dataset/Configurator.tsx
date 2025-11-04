import { Skeleton, TextField, Typography } from "@mui/material";
import { Stack } from "@mui/material";
import { useField } from "@tanstack/react-form";
import { useEffect, useRef } from "react";

import { withForm } from "../filtering/hooks/form";

import { addToDatasetFormOptions } from "./form/shared";
import { SpanSelector } from "./SpanSelector";

import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { DatasetResponse, NestedSpanWithMetricsResponse } from "@/lib/api-client/api-client";

export const Configurator = withForm({
  ...addToDatasetFormOptions,
  props: {} as {
    dataset: DatasetResponse;
    spans: NestedSpanWithMetricsResponse[];
  },
  render: function Render({ form, dataset, spans }) {
    const ref = useRef<HTMLDivElement>(null);
    const { version, isLoading } = useDatasetVersionData(dataset.id, dataset.latest_version_number!);

    useEffect(() => {
      if (!version) return;

      form.setFieldValue(
        "columns",
        version.column_names.map((columnName) => ({
          name: columnName,
          value: "",
          path: "",
        }))
      );
    }, [form, version]);

    const field = useField({ form, name: "columns" as const });

    return isLoading ? (
      <div className="grid grid-cols-[1fr_2fr] gap-2">
        <Skeleton variant="rectangular" height={32} />
        <Skeleton variant="rectangular" height={124} />
      </div>
    ) : (
      <div className="grid grid-cols-[1fr_2fr] gap-2" ref={ref}>
        {field.state.value.map((column, index) => (
          <form.Field mode="array" name={`columns[${index}].value` as const}>
            {(field) => (
              <>
                <div className="grid grid-cols-subgrid col-span-2">
                  <Stack alignItems="flex-start" gap={1}>
                    <Typography variant="body2" fontWeight="medium">
                      {column.name}
                    </Typography>
                    <SpanSelector form={form} spans={spans} name={column.name} container={ref.current!} index={index} />
                  </Stack>
                  <Stack gap={1}>
                    <Typography variant="body2" fontWeight="medium">
                      Extracted Value {column.path && `(${column.path})`}
                    </Typography>
                    <TextField
                      disabled={!column.path}
                      placeholder="Select a span and drill down through its keys to extract data"
                      multiline
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                    />
                  </Stack>
                </div>
              </>
            )}
          </form.Field>
        ))}
      </div>
    );
  },
});
