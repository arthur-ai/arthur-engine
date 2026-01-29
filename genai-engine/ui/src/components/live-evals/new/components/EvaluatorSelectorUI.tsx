import { Autocomplete, Stack, TextField, Typography } from "@mui/material";

type EvaluatorSelectorUIProps = {
  evaluators: string[]; // Just names
  versions: string[]; // Version numbers as strings
  selectedName: string | null;
  selectedVersion: string | null;
  onNameChange: (name: string | null) => void;
  onVersionChange: (version: string | null) => void;
  isVersionsLoading: boolean;
  title?: string;
};

export const EvaluatorSelectorUI = ({
  evaluators,
  versions,
  selectedName,
  selectedVersion,
  onNameChange,
  onVersionChange,
  isVersionsLoading,
  title = "Evaluator and Version",
}: EvaluatorSelectorUIProps) => {
  return (
    <Stack gap={2}>
      <Typography variant="h6" color="text.primary" fontWeight="bold">
        {title}
      </Typography>
      <Stack direction="row" gap={2} width="100%">
        <Autocomplete
          sx={{ flex: 1 }}
          options={evaluators}
          value={selectedName}
          onChange={(_, value) => {
            onNameChange(value);
          }}
          renderInput={(params) => <TextField {...params} label="Evaluator" />}
        />
        <Autocomplete
          sx={{ width: 200 }}
          loading={isVersionsLoading}
          disabled={!selectedName}
          options={versions}
          value={selectedVersion}
          onChange={(_, value) => {
            onVersionChange(value);
          }}
          getOptionLabel={(option) => `v${option}`}
          renderInput={(params) => <TextField {...params} label="Version" />}
        />
      </Stack>
    </Stack>
  );
};
