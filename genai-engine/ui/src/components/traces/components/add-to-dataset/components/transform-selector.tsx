import { Autocomplete, Box, Stack, TextField, Typography } from "@mui/material";
import { alpha, Theme } from "@mui/material/styles";
import { useStore } from "@tanstack/react-form";

import { withFieldGroup } from "../../filtering/hooks/form";
import { addToDatasetFormOptions } from "../form/shared";
import { useExecuteTransform } from "../hooks/useExecuteTransform";
import { MatchStatus, useMatchingVariables } from "../hooks/useMatchingVariables";

import { getNestedValue, getNestedValueWildcard } from "@/components/traces/utils/spans";
import { useTransforms } from "@/hooks/transforms/useTransforms";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import { DatasetVersionMetadataResponse, NestedSpanWithMetricsResponse, TraceTransformResponse } from "@/lib/api-client/api-client";

const getStatusPalette = (theme: Theme, status: MatchStatus) => {
  const palette = {
    "full-match": theme.palette.success,
    partial: theme.palette.warning,
    "no-match": theme.palette.error,
  }[status];

  return {
    backgroundColor: alpha(palette.main, 0.12),
    borderColor: alpha(palette.main, 0.4),
    color: palette.main,
  };
};

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
            const hasWildcard = variableDef.attribute_path.includes("*");
            const data = hasWildcard
              ? getNestedValueWildcard(span.raw_data, variableDef.attribute_path)
              : getNestedValue(span.raw_data, variableDef.attribute_path);

            if (data !== undefined && (Array.isArray(data) ? data.length > 0 : true)) {
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
            if (!value) return;

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
                    <SelectorOption option={option} dataset={latestVersion} />
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

const SelectorOption = ({ option, dataset }: { option: TraceTransformResponse; dataset: DatasetVersionMetadataResponse | undefined }) => {
  const { matchCount, matchStatus, unmatchedTransform } = useMatchingVariables({
    columnNames: dataset?.column_names ?? [],
    variables: option.definition.variables ?? [],
  });

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
          sx={(theme) => {
            const config = getStatusPalette(theme, matchStatus);
            return {
              display: "inline-flex",
              alignItems: "center",
              px: 1,
              py: 0.25,
              borderRadius: 1,
              backgroundColor: config.backgroundColor,
              border: `1px solid ${config.borderColor}`,
              color: config.color,
            };
          }}
        >
          <Typography variant="caption" fontWeight={500} color="inherit">
            {matchCount} of {option.definition.variables.length} match
          </Typography>
        </Box>
        {unmatchedTransform.length > 0 && (
          <Box
            component="span"
            sx={(theme) => {
              const config = getStatusPalette(theme, matchStatus);
              return {
                display: "inline-flex",
                alignItems: "center",
                px: 1,
                py: 0.25,
                borderRadius: 1,
                backgroundColor: alpha(config.color, 0.2),
                color: config.color,
              };
            }}
          >
            <Typography variant="caption" fontWeight={500} color="inherit">
              +{unmatchedTransform.length} new
            </Typography>
          </Box>
        )}
      </Stack>
    </Stack>
  );
};
