import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useState } from "react";

import { agentNotebookStateFormOpts } from "../form";

import { withForm } from "@/components/traces/components/filtering/hooks/form";

export const SubmitButton = withForm({
  ...agentNotebookStateFormOpts,
  // props: {} as {},
  render: function Render({ form }) {
    const [showDialog, setShowDialog] = useState(false);

    const requestTimeParameters = useStore(form.store, (state) => {
      return state.values.templateVariableMapping.filter((v) => v.source.type === "request_time_parameter");
    });

    const hasRequestTimeParameters = requestTimeParameters.length > 0;

    return (
      <>
        <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting]}>
          {([canSubmit, isSubmitting]) => (
            <Button
              type={hasRequestTimeParameters ? "button" : "submit"}
              onClick={hasRequestTimeParameters ? () => setShowDialog(true) : undefined}
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
              <Typography variant="body1">Please fill in the request time parameters for the notebook.</Typography>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowDialog(false)}>Cancel</Button>
            <Button variant="contained" color="primary" onClick={() => form.handleSubmit()}>
              Execute Notebook
            </Button>
          </DialogActions>
        </Dialog>
      </>
    );
  },
});
