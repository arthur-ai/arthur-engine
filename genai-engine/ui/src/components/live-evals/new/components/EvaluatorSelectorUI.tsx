import AddIcon from "@mui/icons-material/Add";
import { Autocomplete, Button, Stack, TextField, Typography } from "@mui/material";

type EvaluatorSelectorUIProps = {
  evaluators: string[];
  versions: string[];
  selectedName: string | null;
  selectedVersion: string | null;
  onNameChange: (name: string | null) => void;
  onVersionChange: (version: string | null) => void;
  isVersionsLoading: boolean;
  title?: string;
  onCreateNew?: () => void;
  isCreateLoading?: boolean;
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
  onCreateNew,
  isCreateLoading,
}: EvaluatorSelectorUIProps) => {
  return (
    <Stack gap={2}>
      <Stack direction="row" gap={2} width="100%" alignItems="center">
        <Typography variant="h6" color="text.primary" fontWeight="bold">
          {title}
        </Typography>
        {onCreateNew && (
          <Button
            loading={isCreateLoading}
            variant="contained"
            disableElevation
            size="small"
            color="primary"
            startIcon={<AddIcon />}
            type="button"
            onClick={onCreateNew}
            sx={{ ml: "auto" }}
          >
            Create New
          </Button>
        )}
      </Stack>
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
