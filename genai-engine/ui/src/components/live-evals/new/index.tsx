import {
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  Paper,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect } from "react";
import z from "zod";

import { useTransforms } from "@/components/datasets/transforms/hooks/useTransforms";
import { useEval } from "@/components/evaluators/hooks/useEval";
import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import NunjucksHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { VariableChip } from "@/components/evaluators/VariableChip";
import { useAppForm, withFieldGroup } from "@/components/traces/components/filtering/hooks/form";
import { getContentHeight } from "@/constants/layout";
import { useDatasets } from "@/hooks/useDatasets";
import { useTask } from "@/hooks/useTask";

type Evaluator = {
  name: string | null;
  version: string | null;
  variables: Record<string, boolean>;
};

type Transform = {
  datasetId: string | null;
  name: string | null;
};

export const LiveEvalsNew = () => {
  const { task } = useTask();
  const { spacing } = useTheme();

  const form = useAppForm({
    defaultValues: {
      evaluator: {
        name: null,
        version: null,
      } as Evaluator,
      transform: {
        datasetId: null,
        name: null,
      } as Transform,
    },
    validators: {
      onChange: z.object({
        evaluator: z.object({
          name: z.string().min(1, "Evaluator name is required"),
          version: z.string().min(1, "Evaluator version is required"),
          variables: z.record(z.string(), z.boolean()),
        }),
        transform: z.object({
          datasetId: z.string().min(1, "Dataset ID is required"),
          name: z.string().min(1, "Transform name is required"),
        }),
      }),
    },
  });

  const evaluator = useStore(form.store, (state) => state.values.evaluator);

  const { eval: evaluatorData } = useEval(task?.id, evaluator.name ?? undefined, evaluator.version ?? undefined);

  useEffect(() => {
    if (evaluatorData) {
      const variables =
        evaluatorData.variables?.reduce(
          (acc, variable) => {
            acc[variable] = true;
            return acc;
          },
          {} as Record<string, boolean>
        ) ?? {};
      form.setFieldValue("evaluator.variables", variables);
    }
  }, [evaluatorData, form]);

  return (
    <Stack
      sx={{
        height: getContentHeight(),
      }}
    >
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack>
          <Typography variant="h5" color="text.primary" fontWeight="bold" mb={0.5}>
            New Live Eval
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create a new live eval to monitor and analyze your model's performance in real-time.
          </Typography>
        </Stack>
      </Box>
      <Stack sx={{ p: 3, width: "100%", flex: 1, overflow: "auto" }} gap={2}>
        <EvaluatorSelector taskId={task?.id ?? ""} form={form} fields="evaluator" />
        {evaluatorData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 items-start" style={{ gap: spacing(2) }}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <NunjucksHighlightedTextField
                value={evaluatorData?.instructions ?? ""}
                onChange={() => {}} // Read-only, no-op
                readOnly
                size="small"
              />
            </Paper>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="body1" color="text.primary" fontWeight="bold">
                Required Variables
              </Typography>
              <FormControl component="fieldset" variant="standard">
                <FormLabel component="legend">Assign Required Variables</FormLabel>
                <FormGroup>
                  {Object.entries(evaluator.variables ?? {}).map(([variable]) => (
                    <form.AppField
                      key={variable}
                      name={`evaluator.variables.${variable}`}
                      children={(field) => (
                        <FormControlLabel
                          control={
                            <Checkbox size="small" checked={field.state.value} onChange={(event) => field.handleChange(event.target.checked)} />
                          }
                          label={<VariableChip variable={variable} />}
                        />
                      )}
                    />
                  ))}
                </FormGroup>
              </FormControl>
            </Paper>
          </div>
        )}
        <TransformSelector taskId={task?.id ?? ""} form={form} fields="transform" />
      </Stack>

      <Box sx={{ p: 3 }} className="mt-auto w-full">
        <form.Subscribe selector={(state) => [state.canSubmit, state.isDirty]}>
          {([canSubmit, isDirty]) => (
            <Button variant="contained" size="large" color="primary" disabled={!canSubmit || !isDirty} fullWidth>
              Create Live Eval
            </Button>
          )}
        </form.Subscribe>
      </Box>
    </Stack>
  );
};

const EvaluatorSelector = withFieldGroup({
  defaultValues: {
    name: null,
    version: null,
  } as Evaluator,
  props: {} as {
    taskId: string;
  },
  render: function Render({ group, taskId }) {
    const evaluators = useEvals(taskId, {
      page: 0,
      pageSize: 10,
      sort: "desc",
    });

    const name = useStore(group.store, (state) => state.values.name);

    const versions = useEvalVersions(taskId, name ?? undefined, {
      page: 0,
      pageSize: 10,
      sort: "desc",
    });

    return (
      <Stack gap={2}>
        <Typography variant="h6" color="text.primary" fontWeight="bold">
          Select an evaluator and a version
        </Typography>
        <Stack direction="row" gap={2} width="100%">
          <group.AppField
            name="name"
            listeners={{
              onChange: () => {
                group.setFieldValue("version", null);
              },
            }}
            children={(field) => (
              <field.MaterialAutocompleteField
                sx={{ flex: 1 }}
                options={evaluators?.evals.map((evaluator) => evaluator.name)}
                renderInput={(params) => <TextField {...params} label="Evaluator" />}
              />
            )}
          />

          <group.AppField
            name="version"
            children={(field) => (
              <field.MaterialAutocompleteField
                multiple={false}
                onBlur={() => {
                  field.handleBlur();
                }}
                sx={{ width: 200 }}
                loading={versions.isLoading}
                disabled={!name}
                options={versions.versions?.map((version) => version.version.toString())}
                getOptionLabel={(option) => `v${option}`}
                renderInput={(params) => <TextField {...params} label="Version" />}
              />
            )}
          />
        </Stack>
      </Stack>
    );
  },
});

const TransformSelector = withFieldGroup({
  defaultValues: {
    datasetId: null,
    name: null,
    version: null,
  } as Transform,
  props: {} as {
    taskId: string;
  },
  render: function Render({ group, taskId }) {
    const datasetId = useStore(group.store, ({ values }) => values.datasetId);

    const datasets = useDatasets(taskId, { page: 0, pageSize: 10, sortOrder: "desc" });
    const transforms = useTransforms(datasetId ?? undefined);

    return (
      <Stack gap={2}>
        <Typography variant="h6" color="text.primary" fontWeight="bold">
          Select a transform
        </Typography>
        <Stack direction="row" gap={2} width="100%">
          <group.AppField
            name="datasetId"
            listeners={{
              onChange: () => {
                group.setFieldValue("name", null);
              },
            }}
            children={(field) => (
              <field.MaterialAutocompleteField
                sx={{ flex: 1 }}
                options={datasets.datasets.map((dataset) => dataset.id)}
                renderInput={(params) => <TextField {...params} label="Dataset" />}
              />
            )}
          />

          <group.AppField
            name="name"
            children={(field) => (
              <field.MaterialAutocompleteField
                sx={{ flex: 1 }}
                disabled={!datasetId}
                options={transforms.data?.map((transform) => transform.name) ?? []}
                renderInput={(params) => <TextField {...params} label="Transform" />}
              />
            )}
          />
        </Stack>
      </Stack>
    );
  },
});
