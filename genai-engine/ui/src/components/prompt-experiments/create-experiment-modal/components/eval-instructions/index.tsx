import { Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Paper, Stack, Typography } from "@mui/material";

import { useEval } from "@/components/evaluators/hooks/useEval";
import { useTask } from "@/hooks/useTask";

type Props = {
  name: string;
  version: number;
  open: boolean;
  onClose: () => void;
};

export const EvalInstructions = ({ name, version, open, onClose }: Props) => {
  const { task } = useTask();

  const evalQuery = useEval(task?.id, name, version.toString());

  return (
    <Dialog open={open} onClose={onClose} aria-labelledby="evaluator-instructions-dialog-title">
      <DialogTitle id="evaluator-instructions-dialog-title">
        {name} (v{version}) - Instructions
      </DialogTitle>
      <DialogContent>
        <Stack component={Paper} sx={{ p: 2 }} alignItems="center">
          {evalQuery.isLoading ? (
            <CircularProgress sx={{ mx: "auto" }} />
          ) : (
            <Typography
              variant="body2"
              component="pre"
              sx={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "monospace", fontSize: "0.875rem" }}
            >
              {evalQuery.eval?.instructions}
            </Typography>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};
