import { Close, PlayArrow } from "@mui/icons-material";
import { Button, Chip, Collapse, Paper, Stack, Typography } from "@mui/material";

const MAX_TRACES = 50;

type SelectionActionBarProps = {
  selectedCount: number;
  onRunEval: () => void;
  onClearSelection: () => void;
};

export const SelectionActionBar = ({ selectedCount, onRunEval, onClearSelection }: SelectionActionBarProps) => {
  return (
    <Collapse in={selectedCount > 0}>
      <Paper
        variant="outlined"
        sx={{
          px: 2,
          py: 1.5,
        }}
      >
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography variant="body2" fontWeight={600}>
            {selectedCount} trace{selectedCount !== 1 ? "s" : ""} selected
          </Typography>

          {selectedCount > MAX_TRACES && <Chip label={`Max ${MAX_TRACES} per test run`} size="small" color="warning" variant="outlined" />}

          <Stack direction="row" spacing={1} sx={{ ml: "auto !important" }}>
            <Button size="small" variant="outlined" startIcon={<Close />} onClick={onClearSelection}>
              Clear
            </Button>
            <Button size="small" variant="contained" startIcon={<PlayArrow />} onClick={onRunEval}>
              Run Eval
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Collapse>
  );
};
