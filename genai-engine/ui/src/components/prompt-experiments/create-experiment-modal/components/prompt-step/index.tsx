import { Box, Button, DialogActions, DialogContent, FormControl, FormHelperText, InputLabel, MenuItem, Select } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import z from "zod";

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

    const { version } = useDatasetVersionData(dataset.id ?? undefined, dataset.version ?? undefined);

    return (
      <>
        <DialogContent>
          <div className="py-2">
            <form.AppField
              name="promptVariableMappings"
              mode="array"
              validators={{
                onSubmit: ({ fieldApi }) => {
                  return fieldApi.parseValueWithSchema(
                    z.array(
                      z.object({
                        source: z.string().min(1, { error: "Column mapping is required" }),
                        target: z.string().min(1),
                      })
                    )
                  );
                },
              }}
            >
              {(field) =>
                field.state.value.map((mapping, index) => (
                  <div key={mapping.target}>
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
                  </div>
                ))
              }
            </form.AppField>
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={onCancel}>Cancel</Button>
          <Box sx={{ flex: 1 }} />
          <Button onClick={() => form.setFieldValue("section", "info")}>Back</Button>
          <Button type="submit" variant="contained">
            Configure Evals
          </Button>
        </DialogActions>
      </>
    );
  },
});
