import { Box, Button, DialogActions, DialogContent, FormControl, FormHelperText, InputLabel, MenuItem, Select } from "@mui/material";
import { useStore } from "@tanstack/react-form";

import { createExperimentModalFormOpts } from "../../form";

import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";

export const PromptStep = withForm({
  ...createExperimentModalFormOpts,
  props: {
    onCancel: () => {},
  },
  render: function Render({ form, onCancel }) {
    const dataset = useStore(form.store, (state) => state.values.info.dataset);
    const hasEvaluators = useStore(form.store, (state) => state.values.info.evaluators.length > 0);

    const { version } = useDatasetVersionData(dataset.id ?? undefined, dataset.version ?? undefined);

    return (
      <>
        <DialogContent>
          <Box sx={{ py: 1 }}>
            <form.AppField name="promptVariableMappings" mode="array">
              {(field) =>
                field.state.value.map((mapping, index) => (
                  <Box key={mapping.target}>
                    <form.AppField name={`promptVariableMappings[${index}].source`}>
                      {(field) => (
                        <FormControl fullWidth error={field.state.meta.errors.length > 0}>
                          <InputLabel required>{mapping.target}</InputLabel>
                          <Select required label={mapping.target} value={field.state.value} onChange={(e) => field.handleChange(e.target.value)}>
                            <MenuItem value="">Select a column</MenuItem>
                            {version?.column_names.map((column) => (
                              <MenuItem key={column} value={column}>
                                {column}
                              </MenuItem>
                            ))}
                          </Select>
                          {field.state.meta.errors.length > 0 && <FormHelperText>{field.state.meta.errors[0]?.message}</FormHelperText>}
                        </FormControl>
                      )}
                    </form.AppField>
                  </Box>
                ))
              }
            </form.AppField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onCancel}>Cancel</Button>
          <Box sx={{ flex: 1 }} />
          <Button onClick={() => form.setFieldValue("section", "info")}>Back</Button>
          <form.Subscribe selector={(state) => [state.isSubmitting]}>
            {([isSubmitting]) => (
              <Button type="submit" variant="contained" loading={!hasEvaluators && isSubmitting}>
                {hasEvaluators ? "Configure Evals" : "Create Experiment"}
              </Button>
            )}
          </form.Subscribe>
        </DialogActions>
      </>
    );
  },
});
