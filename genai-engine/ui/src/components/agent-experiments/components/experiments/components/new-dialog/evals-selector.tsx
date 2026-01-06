import AddIcon from "@mui/icons-material/Add";
import { Autocomplete, Button, Chip, Paper, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";

import type { FormValues } from "./form";

import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useTask } from "@/hooks/useTask";

export const EvalsSelector = withForm({
  defaultValues: {} as FormValues,
  render: function Render({ form }) {
    const { task } = useTask();
    const [currentEval, setCurrentEval] = useState({ name: null as string | null, version: null as string | null });

    const { evals } = useEvals(task?.id, { page: 0, pageSize: 100, sort: "desc" });
    const { versions } = useEvalVersions(task?.id, currentEval.name ?? undefined, { page: 0, pageSize: 100, sort: "desc" });

    const handleAddEval = () => {
      if (!currentEval.name || !currentEval.version) return;

      form.pushFieldValue("evals", { name: currentEval.name, version: currentEval.version });
      setCurrentEval({ name: null, version: null });
    };

    return (
      <Paper component={Stack} gap={2} variant="outlined" p={2}>
        <Stack>
          <Typography variant="body2" color="text.primary">
            Evaluators
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Select the evaluators to use for the experiment.
          </Typography>
        </Stack>
        <Stack direction="row" gap={2} width="100%">
          <Autocomplete
            size="small"
            options={evals?.map((e) => e.name)}
            value={currentEval.name}
            onChange={(_, value) => setCurrentEval({ name: value, version: null })}
            renderInput={(params) => <TextField {...params} label="Evaluator" />}
            sx={{ flex: 1 }}
          />
          <Autocomplete
            size="small"
            disabled={!currentEval.name}
            options={versions?.map((v) => v.version.toString())}
            value={currentEval.version?.toString() ?? null}
            onChange={(_, value) => setCurrentEval((prev) => ({ ...prev, version: value?.toString() ?? null }))}
            renderInput={(params) => <TextField {...params} label="Version" />}
          />
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={handleAddEval}
            disableElevation
            disabled={!currentEval.name || !currentEval.version}
          >
            Add
          </Button>
        </Stack>
        <form.AppField name="evals" mode="array">
          {(field) => (
            <Stack alignItems="flex-start" direction="row" gap={1}>
              {field.state.value.map((evaluator, index) => (
                <Chip key={evaluator.name} label={`${evaluator.name} v${evaluator.version}`} onDelete={() => field.removeValue(index)} />
              ))}
            </Stack>
          )}
        </form.AppField>
      </Paper>
    );
  },
});
