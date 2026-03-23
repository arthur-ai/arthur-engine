import {
  Autocomplete,
  Box,
  Button,
  DialogActions,
  DialogContent,
  Link,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useState } from "react";

import { createExperimentModalFormOpts } from "../../form";
import { EvalInstructions } from "../eval-instructions";

import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";

export const EvalsStep = withForm({
  ...createExperimentModalFormOpts,
  props: {
    onCancel: () => {},
  },
  render: function Render({ form, onCancel }) {
    const [evaluator, setEvaluator] = useState<{ name: string; version: number } | null>(null);

    const evaluators = useStore(form.store, (state) => state.values.evalVariableMappings);
    const dataset = useStore(form.store, (state) => state.values.info.dataset);

    const versionQuery = useDatasetVersionData(dataset.id ?? undefined, dataset.version ?? undefined);

    return (
      <>
        <DialogContent>
          <Stack py={2} gap={2}>
            {evaluators.map((evaluator, index) => (
              <Stack key={index} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 2 }} gap={2} position="relative">
                <Stack alignItems="flex-start">
                  <Link
                    component="button"
                    type="button"
                    variant="body2"
                    fontWeight="bold"
                    underline="hover"
                    className="sticky top-0"
                    onClick={() => setEvaluator(evaluator)}
                  >
                    {evaluator.name} v{evaluator.version}
                  </Link>
                  <Typography variant="body2" color="text.secondary">
                    Map each variable of this evaluator to either a dataset column or the experiment output.
                  </Typography>
                </Stack>
                <form.AppField name={`evalVariableMappings[${index}].variables`} mode="array">
                  {(field) => (
                    <Stack gap={2}>
                      {field.state.value.map((variable, vIndex) => (
                        <Stack
                          key={vIndex}
                          sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 2, backgroundColor: "background.paper" }}
                          gap={2}
                        >
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Typography variant="body2">{variable.name}</Typography>
                            <form.AppField
                              name={`evalVariableMappings[${index}].variables[${vIndex}].sourceType`}
                              listeners={{
                                onChange: () => {
                                  const path = `evalVariableMappings[${index}].variables[${vIndex}].source` as const;
                                  form.setFieldValue(path, "");
                                  form.setFieldMeta(path, (prev) => ({
                                    ...prev,
                                    errorMap: {
                                      ...prev.errorMap,
                                      onSubmit: undefined,
                                    },
                                  }));
                                },
                              }}
                            >
                              {(field) => (
                                <ToggleButtonGroup
                                  value={variable.sourceType}
                                  exclusive
                                  onChange={(e, value) => {
                                    field.handleChange(value);
                                  }}
                                  size="small"
                                >
                                  <ToggleButton value="dataset_column">Dataset Column</ToggleButton>
                                  <ToggleButton value="experiment_output">Experiment Output</ToggleButton>
                                </ToggleButtonGroup>
                              )}
                            </form.AppField>
                          </Stack>
                          <form.Subscribe selector={(state) => state.values.evalVariableMappings[index].variables[vIndex].sourceType}>
                            {(sourceType) => (
                              <Stack>
                                {sourceType === "dataset_column" ? (
                                  <form.AppField name={`evalVariableMappings[${index}].variables[${vIndex}].source`}>
                                    {(field) => {
                                      const selected = versionQuery.version?.column_names.find((c) => c === field.state.value) ?? null;

                                      return (
                                        <Autocomplete
                                          options={versionQuery.version?.column_names ?? []}
                                          getOptionLabel={(option) => option}
                                          value={selected}
                                          onChange={(_, value) => {
                                            field.handleChange(value ?? "");
                                          }}
                                          renderInput={(params) => (
                                            <TextField
                                              {...params}
                                              label="Dataset Column"
                                              variant="filled"
                                              error={field.state.meta.errors.length > 0}
                                              helperText={field.state.meta.errors[0]?.message}
                                            />
                                          )}
                                        />
                                      );
                                    }}
                                  </form.AppField>
                                ) : (
                                  <Paper sx={(theme) => ({ p: 1, backgroundColor: theme.palette.background.default })} variant="outlined">
                                    <Typography variant="body2" sx={{ fontStyle: "italic" }}>
                                      This variable will receive the full output from the prompt execution.
                                    </Typography>
                                  </Paper>
                                )}
                              </Stack>
                            )}
                          </form.Subscribe>
                        </Stack>
                      ))}
                    </Stack>
                  )}
                </form.AppField>
              </Stack>
            ))}
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={onCancel}>Cancel</Button>
          <Box sx={{ flex: 1 }} />
          <Button onClick={() => form.setFieldValue("section", "prompts")}>Back</Button>
          <form.Subscribe selector={(state) => [state.isSubmitting]}>
            {([isSubmitting]) => (
              <Button type="submit" variant="contained" loading={isSubmitting}>
                Create Experiment
              </Button>
            )}
          </form.Subscribe>
        </DialogActions>

        {evaluator && <EvalInstructions name={evaluator.name} version={evaluator.version} open={!!evaluator} onClose={() => setEvaluator(null)} />}
      </>
    );
  },
});
