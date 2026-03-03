import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { Alert, Autocomplete, Box, Card, CardContent, Chip, CircularProgress, Stack, TextField, Tooltip, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect } from "react";

import { withFieldGroup } from "@arthur/shared-components";
import type { ContinuousEvalTransformVariableMappingRequest } from "@/lib/api-client/api-client";

type VariableMappingFormState = {
  variableMappings: ContinuousEvalTransformVariableMappingRequest[];
};

export const VariableMappingSection = withFieldGroup({
  defaultValues: {
    variableMappings: [],
  } as VariableMappingFormState,
  props: {} as {
    eval_variables: string[];
    transform_variables: string[];
    matching_variables: string[];
    disabled?: boolean;
    isLoading?: boolean;
  },
  render: function Render({ group, eval_variables, transform_variables, matching_variables, disabled = false, isLoading = false }) {
    const mappings = useStore(group.store, (state) => state.values.variableMappings);

    // Auto-populate mappings when matching variables are detected and no mappings exist yet
    useEffect(() => {
      if (matching_variables.length > 0 && mappings.length === 0) {
        group.setFieldValue(
          "variableMappings",
          matching_variables.map((variable) => ({
            eval_variable: variable,
            transform_variable: variable,
          }))
        );
      }
    }, [matching_variables, mappings.length, group]);

    const handleMappingChange = (evalVariable: string, transformVariable: string | null) => {
      const newMappings = mappings.filter((m) => m.eval_variable !== evalVariable);

      if (transformVariable) {
        newMappings.push({
          eval_variable: evalVariable,
          transform_variable: transformVariable,
        });
      }

      group.setFieldValue("variableMappings", newMappings);
    };

    const getMappedTransformVariable = (evalVariable: string): string | null => {
      const mapping = mappings.find((m) => m.eval_variable === evalVariable);
      return mapping?.transform_variable ?? null;
    };

    const isAutoMatched = (evalVariable: string): boolean => {
      return matching_variables.includes(evalVariable);
    };

    const unmappedVariables = eval_variables.filter((v) => !getMappedTransformVariable(v));

    if (isLoading) {
      return (
        <Box className="flex justify-center py-4">
          <CircularProgress size={24} />
        </Box>
      );
    }

    if (eval_variables.length === 0) {
      return (
        <Alert severity="info" sx={{ mt: 1 }}>
          This evaluator has no variables to map.
        </Alert>
      );
    }

    return (
      <Stack gap={2}>
        <Stack>
          <Typography variant="h6" color="text.primary" fontWeight="bold">
            Variable Mapping
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Map each evaluator variable to a transform variable that will provide its value at runtime.
          </Typography>
        </Stack>

        {unmappedVariables.length > 0 && (
          <Alert severity="warning" sx={{ py: 0.5 }}>
            {unmappedVariables.length} variable{unmappedVariables.length > 1 ? "s" : ""} still need{unmappedVariables.length === 1 ? "s" : ""} to be
            mapped: {unmappedVariables.join(", ")}
          </Alert>
        )}

        <Stack gap={2}>
          {eval_variables.map((evalVariable) => {
            const mappedValue = getMappedTransformVariable(evalVariable);
            const autoMatched = isAutoMatched(evalVariable);

            return (
              <Card key={evalVariable} variant="outlined">
                <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
                  <Stack gap={1.5}>
                    <Stack direction="row" alignItems="center" gap={1}>
                      <Typography variant="subtitle2" fontWeight={600}>
                        {evalVariable}
                      </Typography>
                      {autoMatched && mappedValue && (
                        <Tooltip title="Auto-matched based on matching variable names">
                          <Chip
                            icon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
                            label="Auto-matched"
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ height: 22, "& .MuiChip-label": { px: 1, fontSize: "0.7rem" } }}
                          />
                        </Tooltip>
                      )}
                    </Stack>

                    <Autocomplete
                      size="small"
                      disabled={disabled}
                      options={transform_variables}
                      value={mappedValue}
                      onChange={(_, value) => handleMappingChange(evalVariable, value)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Transform Variable"
                          placeholder="Select a transform variable"
                          error={!mappedValue}
                          helperText={!mappedValue ? "Required" : undefined}
                        />
                      )}
                      isOptionEqualToValue={(option, value) => option === value}
                    />
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      </Stack>
    );
  },
});

export default VariableMappingSection;
