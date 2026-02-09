import { Autocomplete, Box, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";

import { withFieldGroup } from "../../filtering/hooks/form";
import { addToDatasetFormOptions } from "../form/shared";
import { useExecuteTransform } from "../hooks/useExecuteTransform";
import { MatchStatus, useMatchingVariables } from "../hooks/useMatchingVariables";

import { getNestedValue } from "@/components/traces/utils/spans";
import { useTransforms } from "@/hooks/transforms/useTransforms";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import { DatasetVersionMetadataResponse, NestedSpanWithMetricsResponse, TraceTransformResponse } from "@/lib/api-client/api-client";

export const TransformSelector = withFieldGroup({
  ...addToDatasetFormOptions,
  props: {} as {
    traceId: string;
    flatSpans: NestedSpanWithMetricsResponse[];
  },
  render: function Render({ group, traceId, flatSpans }) {
    const dataset = useStore(group.store, (state) => state.values.dataset);
    const transform = useStore(group.store, (state) => state.values.transform);

    const { latestVersion } = useDatasetLatestVersion(dataset);

    const { data } = useTransforms();
    const transforms = data?.transforms;

    const selectedTransform = transforms?.find((t) => t.id === transform);

    const executeTransformMutation = useExecuteTransform(traceId, {
      onSuccess: (data) => {
        if (!data.variables.length || !selectedTransform) return;

        const executedColumns = data.variables.map((variable) => {
          const variableDef = selectedTransform.definition.variables.find((v) => v.variable_name === variable.name);

          if (!variableDef) {
            return {
              name: variable.name,
              value: variable.value,
              path: "",
              span_name: "",
              attribute_path: "",
            };
          }

          // Validate that the path exists in the trace data
          const span = flatSpans.find((s) => s.span_name === variableDef.span_name);
          let validatedPath = "";
          let validatedSpanName = "";
          let validatedAttributePath = "";

          if (span) {
            // Check if the attribute path exists
            const data = getNestedValue(span.raw_data, variableDef.attribute_path);

            if (data) {
              validatedPath = `${variableDef.span_name}.${variableDef.attribute_path}`;
              validatedSpanName = variableDef.span_name;
              validatedAttributePath = variableDef.attribute_path;
            }
          }

          return {
            name: variable.name,
            value: variable.value,
            path: validatedPath,
            span_name: validatedSpanName,
            attribute_path: validatedAttributePath,
          };
        });

        const existingDatasetColumns = latestVersion?.column_names || [];
        const executedColumnNames = new Set(executedColumns.map((col) => col.name));

        // Create columns for dataset columns that aren't in the transform
        const datasetOnlyColumns = existingDatasetColumns
          .filter((columnName) => !executedColumnNames.has(columnName))
          .map((columnName) => ({
            name: columnName,
            value: "",
            path: "",
            span_name: "",
            attribute_path: "",
          }));

        group.setFieldValue("columns", [...executedColumns, ...datasetOnlyColumns]);
      },
    });

    return (
      <group.Field
        name="transform"
        listeners={{
          onChange: async ({ value }) => {
            if (!traceId) return group.setFieldValue("columns", []);

            await executeTransformMutation.mutateAsync({ transformId: value });
          },
        }}
      >
        {(field) => {
          const selected = transforms?.find((t) => t.id === field.state.value) ?? null;

          return (
            <Autocomplete
              loading={executeTransformMutation.isPending}
              options={transforms ?? []}
              value={selected}
              disabled={!dataset}
              disablePortal
              sx={{ flex: 1 }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Transform"
                  helperText={
                    !dataset ? "Select a dataset first" : !transforms ? "No transforms available for this dataset" : "Select a saved transform"
                  }
                />
              )}
              onChange={(_event, value) => field.handleChange(value?.id ?? "")}
              renderOption={(props, option) => {
                return (
                  <li {...props} key={option.id}>
                    <SelectorOption option={option} dataset={latestVersion!} />
                  </li>
                );
              }}
              getOptionLabel={(option) => option.name}
            />
          );
        }}
      </group.Field>
    );
  },
});

const STATUS_CONFIG: Record<MatchStatus, { backgroundColor: string; borderColor: string; color: string }> = {
  "full-match": { backgroundColor: "var(--color-green-50)", borderColor: "var(--color-green-200)", color: "var(--color-green-700)" },
  partial: { backgroundColor: "var(--color-amber-50)", borderColor: "var(--color-amber-200)", color: "var(--color-amber-700)" },
  "no-match": { backgroundColor: "var(--color-red-50)", borderColor: "var(--color-red-200)", color: "var(--color-red-700)" },
};

const SelectorOption = ({ option, dataset }: { option: TraceTransformResponse; dataset: DatasetVersionMetadataResponse }) => {
  const { matchCount, matchStatus, unmatchedTransform } = useMatchingVariables({
    columnNames: dataset?.column_names ?? [],
    variables: option.definition.variables ?? [],
  });

  const config = STATUS_CONFIG[matchStatus];

  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ width: "100%" }}>
      <Stack direction="column">
        <Typography variant="body2" fontWeight="medium">
          {option.name}
        </Typography>
        {option.description && (
          <Typography variant="body2" color="text.secondary">
            {option.description}
          </Typography>
        )}
      </Stack>
      <Stack direction="row" gap={0.5} alignItems="center">
        <Box
          component="span"
          sx={{
            display: "inline-flex",
            alignItems: "center",
            px: 1,
            py: 0.25,
            borderRadius: 1,
            "--background-color": config.backgroundColor,
            "--border-color": config.borderColor,
            "--color": config.color,
          }}
          className="bg-(--background-color) border-(--border-color) border"
        >
          <Typography variant="caption" fontWeight={500} className="text-(--color)">
            {matchCount} of {option.definition.variables.length} match
          </Typography>
        </Box>
        {unmatchedTransform.length > 0 && (
          <Box
            component="span"
            sx={{
              display: "inline-flex",
              alignItems: "center",
              px: 1,
              py: 0.25,
              borderRadius: 1,
              "--background-color": config.borderColor,
              "--color": config.color,
            }}
            className="bg-(--background-color)"
          >
            <Typography variant="caption" fontWeight={500} className="text-(--color)">
              +{unmatchedTransform.length} new
            </Typography>
          </Box>
        )}
      </Stack>
    </Stack>
  );
};
