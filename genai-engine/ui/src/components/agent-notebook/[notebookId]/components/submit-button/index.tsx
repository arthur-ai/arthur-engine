import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useState } from "react";

import { agentNotebookStateFormOpts } from "../../form";

import { VariableChip } from "@/components/evaluators/VariableChip";
import { withForm } from "@/components/traces/components/filtering/hooks/form";

export const SubmitButton = withForm({
  ...agentNotebookStateFormOpts,
  render: function Render({ form }) {
    const [showDialog, setShowDialog] = useState(false);

    const hasRequestTimeParameters = useStore(form.store, (state) => {
      return state.values.templateVariableMapping.some((v) => v.source.type === "request_time_parameter");
    });

    const openDialog = () => {
      // Reconcile requestTimeParameters from the current templateVariableMapping.
      const currentMapping = form.getFieldValue("templateVariableMapping").filter((v) => v.source.type === "request_time_parameter");
      const existing = form.getFieldValue("requestTimeParameters");
      const byName = new Map(existing.map((p) => [p.name, p.value]));

      form.setFieldValue(
        "requestTimeParameters",
        currentMapping.map((item) => ({
          name: item.variable_name,
          value: byName.get(item.variable_name) ?? "",
        }))
      );
      setShowDialog(true);
    };

    return (
      <>
        <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
          {([canSubmit, isSubmitting]) => (
            <Button
              type={hasRequestTimeParameters ? "button" : "submit"}
              onClick={hasRequestTimeParameters ? openDialog : undefined}
              variant="contained"
              color="primary"
              startIcon={<PlayArrowIcon />}
              disabled={!canSubmit}
              loading={isSubmitting}
            >
              Execute Notebook
            </Button>
          )}
        </form.Subscribe>

        <Dialog open={showDialog} onClose={() => setShowDialog(false)} fullWidth>
          <DialogTitle>Fill Request Time Parameters</DialogTitle>
          <DialogContent dividers>
            <Stack gap={2}>
              <Typography variant="body2" color="text.secondary">
                These values are passed directly to the execution thread and are not stored in the database.
              </Typography>
              <form.AppField name="requestTimeParameters" mode="array">
                {(field) => (
                  <Box className="grid grid-cols-[auto_1fr]" sx={{ rowGap: 2 }}>
                    {field.state.value.map((_item, index) => (
                      <Box key={index} className="grid grid-cols-subgrid col-span-2 items-center" sx={{ gap: 2 }}>
                        <form.Subscribe selector={(state) => state.values.requestTimeParameters[index].name}>
                          {(name) => <VariableChip variable={name} />}
                        </form.Subscribe>
                        <form.AppField name={`requestTimeParameters[${index}].value`}>
                          {(field) => (
                            <TextField
                              size="small"
                              value={field.state.value}
                              onChange={(e) => field.handleChange(e.target.value)}
                              label="Value"
                              fullWidth
                            />
                          )}
                        </form.AppField>
                      </Box>
                    ))}
                  </Box>
                )}
              </form.AppField>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowDialog(false)}>Cancel</Button>
            <Button
              variant="contained"
              color="primary"
              onClick={() => {
                form.handleSubmit();
                setShowDialog(false);
              }}
            >
              Execute Notebook
            </Button>
          </DialogActions>
        </Dialog>
      </>
    );
  },
});
