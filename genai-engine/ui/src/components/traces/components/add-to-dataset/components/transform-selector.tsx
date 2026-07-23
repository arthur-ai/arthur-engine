import { Autocomplete, Box, Stack, TextField, Typography } from "@mui/material";
import { alpha, Theme } from "@mui/material/styles";
import { useStore } from "@tanstack/react-form";

import { withFieldGroup } from "../../filtering/hooks/form";
import { addToDatasetFormOptions, resolveSchemaColumns } from "../form/shared";
import { useExecuteTransform } from "../hooks/useExecuteTransform";
import { MatchStatus, useMatchingVariables } from "../hooks/useMatchingVariables";

import { getNestedValue, getNestedValueWildcard } from "@/components/traces/utils/spans";
import { useTransformVersions } from "@/components/transforms/hooks/useTransformVersions";
import { useTransforms } from "@/hooks/transforms/useTransforms";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import { NestedSpanWithMetricsResponse, TraceTransformResponse } from "@/lib/api-client/api-client";

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
    // The dataset's current columns (persisted schema, or pending columns the
    // user added this session). The first-addition fallback to the transform's
    // variables is applied where consumed — see resolveSchemaColumns.
    datasetColumns: string[];
  },
  render: function Render({ group, traceId, flatSpans, datasetColumns }) {
    const dataset = useStore(group.store, (state) => state.values.dataset);
    const transform = useStore(group.store, (state) => state.values.transform);

    const { isLoading: isLoadingLatestVersion } = useDatasetLatestVersion(dataset);

    const { data } = useTransforms();
    const transforms = data?.transforms;

    const selectedTransform = transforms?.find((t) => t.id === transform);

    const { data: selectedTransformVersions = [] } = useTransformVersions(selectedTransform?.id);
    const selectedTransformDefinition = selectedTransformVersions[0]?.definition;

    const executeTransformMutation = useExecuteTransform(traceId, {
      onSuccess: (executionResult) => {
        if (!executionResult.variables.length || !selectedTransform || !selectedTransformDefinition) return;

        // Skip only while the dataset schema query is still loading (e.g. a stale
        // mutation resolved after the user switched datasets). A first-addition
        // dataset has no persisted version yet but must still be filled.
        if (isLoadingLatestVersion) return;

        const transformVariablesByName = new Map(selectedTransformDefinition.variables.map((v) => [v.variable_name, v]));
        const executedValuesByName = new Map(executionResult.variables.map((v) => [v.name, v.value]));

        // The row schema is the source of truth: iterate its columns and fill
        // values from any matching transform variable (on a first addition the
        // transform's variables ARE the schema). Variables that don't match a
        // column are intentionally dropped here; the Configurator surfaces them
        // in an inline warning.
        const columns = resolveSchemaColumns(datasetColumns, selectedTransformDefinition.variables).map((columnName) => {
          const variableDef = transformVariablesByName.get(columnName);

          if (!variableDef) {
            return {
              name: columnName,
              value: "",
              path: "",
              span_name: "",
              attribute_path: "",
            };
          }

          const span = flatSpans.find((s) => s.span_name === variableDef.span_name);
          let validatedPath = "";
          let validatedSpanName = "";
          let validatedAttributePath = "";

          if (span) {
            const hasWildcard = variableDef.attribute_path.includes("*");
            const extracted = hasWildcard
              ? getNestedValueWildcard(span.raw_data, variableDef.attribute_path)
              : getNestedValue(span.raw_data, variableDef.attribute_path);

            if (extracted !== undefined && (Array.isArray(extracted) ? extracted.length > 0 : true)) {
              validatedPath = `${variableDef.span_name}.${variableDef.attribute_path}`;
              validatedSpanName = variableDef.span_name;
              validatedAttributePath = variableDef.attribute_path;
            }
          }

          return {
            name: columnName,
            value: executedValuesByName.get(columnName) ?? "",
            path: validatedPath,
            span_name: validatedSpanName,
            attribute_path: validatedAttributePath,
          };
        });

        group.setFieldValue("columns", columns);
      },
    });

    return (
      <group.Field
        name="transform"
        listeners={{
          onChange: async ({ value }) => {
            if (!traceId) return group.setFieldValue("columns", []);
            // Clearing the transform discards its auto-filled columns; for a
            // schema'd dataset the Configurator re-seeds empty schema columns,
            // for a first addition nothing stale is left behind in form state.
            if (!value) return group.setFieldValue("columns", []);

            await executeTransformMutation.mutateAsync({ transformId: value });
          },
        }}
      >
        {(field) => {
          const selected = transforms?.find((t) => t.id === field.state.value) ?? null;
          const isDisabled = !dataset || isLoadingLatestVersion;
          const helperText = !dataset
            ? "Select a dataset first"
            : isLoadingLatestVersion
              ? "Loading dataset schema…"
              : !transforms
                ? "No transforms available for this dataset"
                : "Select a saved transform";

          return (
            <Autocomplete
              loading={executeTransformMutation.isPending}
              options={transforms ?? []}
              value={selected}
              disabled={isDisabled}
              disablePortal
              sx={{ flex: 1 }}
              renderInput={(params) => <TextField {...params} label="Transform" helperText={helperText} />}
              onChange={(_event, value) => field.handleChange(value?.id ?? "")}
              renderOption={(props, option) => {
                return (
                  <li {...props} key={option.id}>
                    <SelectorOption option={option} columnNames={datasetColumns} />
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

const SelectorOption = ({ option, columnNames }: { option: TraceTransformResponse; columnNames: string[] }) => {
  const { data: versions = [] } = useTransformVersions(option.id);
  const definition = versions[0]?.definition;
  const { matchCount, matchStatus, unmatchedTransform } = useMatchingVariables({
    columnNames,
    variables: definition?.variables ?? [],
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
            {matchCount} of {definition?.variables.length ?? 0} match
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
