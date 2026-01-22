import { Autocomplete, Button, Chip, Divider, Paper, Stack, TextField, Typography } from "@mui/material";
import CircularProgress from "@mui/material/CircularProgress";

type EvaluatorOption = { name: string };
type VersionOption = { version: number };

type EvaluatorsSelectorUIProps = {
  evaluators: EvaluatorOption[];
  versions: VersionOption[];
  selectedEvaluator: EvaluatorOption | null;
  selectedVersion: VersionOption | null;
  selectedEvals: Array<{ name: string; version: number }>;
  onSelectEvaluator: (evaluator: EvaluatorOption | null) => void;
  onSelectVersion: (version: VersionOption | null) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  isAdding: boolean;
  error?: string | null;
  title?: string;
  description?: string;
};

export const EvaluatorsSelectorUI = ({
  evaluators,
  versions,
  selectedEvaluator,
  selectedVersion,
  selectedEvals,
  onSelectEvaluator,
  onSelectVersion,
  onAdd,
  onRemove,
  isAdding,
  error,
  title = "Select Evaluator and Version",
  description = "Choose the evaluator that will assess the agent responses.",
}: EvaluatorsSelectorUIProps) => {
  return (
    <Stack component={Paper} variant="outlined" p={2}>
      <Stack>
        <Typography variant="body2" color="text.primary" fontWeight="bold">
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      </Stack>
      <Divider sx={{ my: 2 }} />
      <Stack gap={2}>
        <Stack direction="row" gap={2} width="100%">
          <Autocomplete
            size="small"
            sx={{ flex: 1 }}
            options={evaluators}
            value={selectedEvaluator}
            getOptionLabel={(option) => option.name}
            renderInput={(params) => <TextField {...params} label="Evaluator" error={!!error} />}
            onChange={(_, value) => {
              onSelectEvaluator(value);
            }}
          />
          <Autocomplete
            size="small"
            disabled={!selectedEvaluator}
            options={versions}
            value={selectedVersion}
            getOptionLabel={(option) => `v${option.version}`}
            renderInput={(params) => <TextField {...params} label="Version" error={!!error} />}
            onChange={(_, value) => {
              onSelectVersion(value);
            }}
            sx={{ flex: 1 }}
          />
          <Button
            disableElevation
            disabled={!selectedEvaluator || !selectedVersion || !!error}
            variant="contained"
            color="primary"
            onClick={onAdd}
            startIcon={isAdding ? <CircularProgress size={16} color="inherit" /> : null}
          >
            Add
          </Button>
        </Stack>
        {error && (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        )}
        <Stack direction="row" gap={2}>
          {selectedEvals.map((evaluator, index) => (
            <Chip key={`${evaluator.name}-${evaluator.version}`} label={`${evaluator.name} v${evaluator.version}`} onDelete={() => onRemove(index)} />
          ))}
        </Stack>
      </Stack>
    </Stack>
  );
};
