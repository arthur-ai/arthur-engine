import AddIcon from "@mui/icons-material/Add";
import {
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Divider,
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
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import z from "zod";

import { useCreateContinuousEval } from "../hooks/useCreateContinuousEval";

import { useEval } from "@/components/evaluators/hooks/useEval";
import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import NunjucksHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { VariableChip } from "@/components/evaluators/VariableChip";
import { useAppForm, withFieldGroup } from "@/components/traces/components/filtering/hooks/form";
import { useCreateTransformMutation } from "@/components/transforms/hooks/useCreateTransformMutation";
import { useTransforms } from "@/components/transforms/hooks/useTransforms";
import TransformFormModal from "@/components/transforms/TransformFormModal";
import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";

type Evaluator = {
  name: string | null;
  version: string | null;
  variables: Record<string, boolean>;
};

type Transform = {
  transformId: string | null;
};

export const LiveEvalsNew = () => {
  const { task } = useTask();
  const { spacing } = useTheme();

  const navigate = useNavigate();

  const form = useAppForm({
    defaultValues: {
      name: "",
      description: "",
      evaluator: {
        name: null,
        version: null,
      } as Evaluator,
      transform: {
        transformId: null,
      } as Transform,
    },
    validators: {
      onChange: z.object({
        name: z.string().min(1, "Name is required"),
        description: z.string(),
        evaluator: z.object({
          name: z.string().min(1, "Evaluator name is required"),
          version: z.string().min(1, "Evaluator version is required"),
          variables: z.record(z.string(), z.boolean()),
        }),
        transform: z.object({
          transformId: z.string().min(1, "Transform ID is required"),
        }),
      }),
    },
    onSubmit: async ({ value }) => {
      const { id } = await createContinuousEval.mutateAsync({
        name: value.name,
        description: value.description,
        llm_eval_name: value.evaluator.name!,
        llm_eval_version: value.evaluator.version!,
        transform_id: value.transform.transformId!,
      });

      navigate(`/tasks/${task?.id}/continuous-evals/${id}`);
    },
  });

  const createContinuousEval = useCreateContinuousEval();

  const evaluator = useStore(form.store, (state) => state.values.evaluator);

  const { eval: evaluatorData } = useEval(task?.id, evaluator.name ?? undefined, evaluator.version ?? undefined);

  // Initialize variables when evaluator data loads
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
      component="form"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();

        form.handleSubmit();
      }}
      sx={{ height: getContentHeight() }}
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
            New Continuous Eval
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create a new continuous eval to monitor and analyze your model's performance in real-time.
          </Typography>
        </Stack>
      </Box>
      <Stack sx={{ p: 3, width: "100%", flex: 1, overflow: "auto" }} gap={2}>
        <Typography variant="h6" color="text.primary" fontWeight="bold">
          General Information
        </Typography>

        <DetailsFieldGroup
          form={form}
          fields={{
            name: "name",
            description: "description",
          }}
        />

        <Divider sx={{ my: 2 }} />

        <EvaluatorSelector taskId={task?.id ?? ""} form={form} fields="evaluator" />

        {evaluatorData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 items-start" style={{ gap: spacing(2) }}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <NunjucksHighlightedTextField value={evaluatorData?.instructions ?? ""} onChange={() => {}} readOnly size="small" />
            </Paper>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="body1" color="text.primary" fontWeight="bold">
                Variable Requirements
              </Typography>
              <FormControl component="fieldset" variant="standard">
                <FormLabel component="legend">Mark as required (eval won't run if missing)</FormLabel>
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

        <Divider sx={{ my: 2 }} />

        <TransformSelector taskId={task?.id ?? ""} form={form} fields="transform" />
      </Stack>

      <Box sx={{ p: 3, borderTop: 1, borderColor: "divider" }} className="mt-auto w-full">
        <form.Subscribe selector={(state) => [state.canSubmit, state.isDirty, state.isSubmitting]}>
          {([canSubmit, isDirty, isSubmitting]) => (
            <Button variant="contained" size="large" color="primary" disabled={!canSubmit || !isDirty} loading={isSubmitting} fullWidth type="submit">
              Create Continuous Eval
            </Button>
          )}
        </form.Subscribe>
      </Box>
    </Stack>
  );
};

export const DetailsFieldGroup = withFieldGroup({
  defaultValues: {
    name: "",
    description: "",
  },
  render: function Render({ group }) {
    return (
      <Stack gap={2}>
        <group.AppField
          name="name"
          children={(field) => (
            <TextField
              autoFocus
              label="Eval Name"
              type="text"
              fullWidth
              variant="outlined"
              required
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
            />
          )}
        />

        <group.AppField
          name="description"
          children={(field) => (
            <TextField
              multiline
              rows={3}
              label="Description"
              type="text"
              fullWidth
              variant="outlined"
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.errors.length > 0}
            />
          )}
        />
      </Stack>
    );
  },
});

export const EvaluatorSelector = withFieldGroup({
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
          Evaluator and Version
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

export const TransformSelector = withFieldGroup({
  defaultValues: {
    transformId: null,
  } as Transform,
  props: {} as {
    taskId: string;
  },
  render: function Render({ group, taskId }) {
    const [openCreateTransformModal, setOpenCreateTransformModal] = useState(false);
    const transforms = useTransforms(taskId ?? undefined);

    const createTransform = useCreateTransformMutation(taskId, async (data) => {
      await transforms.refetch();

      setOpenCreateTransformModal(false);

      group.setFieldValue("transformId", data.id);
    });

    return (
      <>
        <Stack gap={2}>
          <Stack direction="row" gap={2} width="100%" alignItems="center">
            <Typography variant="h6" color="text.primary" fontWeight="bold">
              Transform
            </Typography>
            <Button
              loading={createTransform.isPending}
              variant="contained"
              disableElevation
              size="small"
              color="primary"
              startIcon={<AddIcon />}
              type="button"
              onClick={() => {
                setOpenCreateTransformModal(true);
              }}
              sx={{ ml: "auto" }}
            >
              Create New
            </Button>
          </Stack>
          <Stack direction="row" gap={2} width="100%">
            <group.AppField
              name="transformId"
              children={(field) => {
                const selected = transforms.data?.find((transform) => transform.id === field.state.value);

                return (
                  <Autocomplete
                    sx={{ flex: 1 }}
                    loading={transforms.isLoading}
                    options={transforms.data ?? []}
                    multiple={false}
                    value={selected ?? null}
                    onChange={(_, value) => {
                      field.handleChange(value?.id ?? "");
                    }}
                    getOptionLabel={(option) => option.name}
                    isOptionEqualToValue={(option, value) => option.id === value.id}
                    getOptionKey={(option) => option.id}
                    renderInput={(params) => <TextField {...params} label="Transform" />}
                  />
                );
              }}
            />
          </Stack>
        </Stack>
        <TransformFormModal
          open={openCreateTransformModal}
          onClose={() => {
            setOpenCreateTransformModal(false);
          }}
          onSubmit={async (name, description, definition) =>
            void createTransform.mutateAsync({
              name,
              description,
              definition,
            })
          }
          isLoading={createTransform.isPending}
          taskId={taskId}
          initialTransform={undefined}
        />
      </>
    );
  },
});
