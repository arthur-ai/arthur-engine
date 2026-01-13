import { Autocomplete, Button, Chip, Divider, Paper, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { NewAgentExperimentFormData } from "../form";

import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import { withFieldGroup } from "@/components/traces/components/filtering/hooks/form";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticEvalVariableMappingInput } from "@/lib/api-client/api-client";

export const EvaluatorsSelector = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "evals">,
  render: function Render({ group }) {
    const { task } = useTask();
    const { api } = useApi()!;
    const [currentEvaluator, setCurrentEvaluator] = useState<{ name: string | null; version: number | null }>({ name: null, version: null });
    const { evals } = useEvals(task?.id, { page: 0, pageSize: 100, sort: "desc" });

    const { versions } = useEvalVersions(task?.id, currentEvaluator.name ?? undefined, { page: 0, pageSize: 100, sort: "desc" });

    const addEval = useMutation({
      mutationFn: async () => {
        if (!currentEvaluator.name || !currentEvaluator.version) return;
        const response = await api.getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet(
          currentEvaluator.name,
          currentEvaluator.version.toString(),
          task!.id
        );

        return response.data;
      },
      onSuccess: (data) => {
        if (!data) return;

        const mapping =
          data.variables?.map((v) => ({ source: { type: "experiment_output" }, variable_name: v }) as AgenticEvalVariableMappingInput) ?? [];

        group.pushFieldValue("evals", { name: data.name, version: data.version ?? 1, variable_mapping: mapping, transform_id: "" });
        setCurrentEvaluator({ name: null, version: null });
      },
    });

    const selectedEvaluator = evals.find((e) => e.name === currentEvaluator.name) ?? null;
    const selectedVersion = versions.find((v) => v.version === currentEvaluator.version) ?? null;

    const currentAlreadyAdded = useStore(group.store, (state) =>
      state.values.evals.some((e) => e.name === currentEvaluator.name && e.version === currentEvaluator.version)
    );

    const handleAddEvaluator = async () => {
      if (!currentEvaluator.name || !currentEvaluator.version || currentAlreadyAdded) return;

      await addEval.mutateAsync();
      setCurrentEvaluator({ name: null, version: null });
    };

    return (
      <Stack component={Paper} variant="outlined" p={2}>
        <Stack>
          <Typography variant="body2" color="text.primary" fontWeight="bold">
            Select Evaluator and Version
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Choose the evaluator that will assess the agent responses.
          </Typography>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <Stack gap={2}>
          <Stack direction="row" gap={2} width="100%">
            <Autocomplete
              size="small"
              sx={{ flex: 1 }}
              options={evals}
              value={selectedEvaluator}
              getOptionLabel={(option) => option.name}
              renderInput={(params) => <TextField {...params} label="Evaluator" error={currentAlreadyAdded} />}
              onChange={(_, value) => {
                setCurrentEvaluator({ name: value?.name ?? null, version: null });
              }}
            />
            <Autocomplete
              size="small"
              disabled={!currentEvaluator.name}
              options={versions}
              value={selectedVersion}
              getOptionLabel={(option) => `v${option.version}`}
              renderInput={(params) => <TextField {...params} label="Version" error={currentAlreadyAdded} />}
              onChange={(_, value) => {
                setCurrentEvaluator({ name: currentEvaluator.name, version: value?.version ?? null });
              }}
              sx={{ flex: 1 }}
            />
            <Button
              disableElevation
              loading={addEval.isPending}
              disabled={!currentEvaluator.name || !currentEvaluator.version || currentAlreadyAdded}
              variant="contained"
              color="primary"
              onClick={handleAddEvaluator}
            >
              Add
            </Button>
          </Stack>
          {currentAlreadyAdded && (
            <Typography variant="body2" color="error">
              This evaluator and version have already been added!
            </Typography>
          )}
          <group.AppField name="evals" mode="array">
            {(field) => (
              <Stack direction="row" gap={2}>
                {field.state.value.map((evaluator, index) => (
                  <Chip
                    key={`${evaluator.name}-${evaluator.version}`}
                    label={`${evaluator.name} v${evaluator.version}`}
                    onDelete={() => field.removeValue(index)}
                  />
                ))}
              </Stack>
            )}
          </group.AppField>
        </Stack>
      </Stack>
    );
  },
});
