import { MustacheHighlightedTextField } from "@arthur/shared-components";
import { useAppForm, withFieldGroup } from "@arthur/shared-components";
import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import {
  Autocomplete,
  Box,
  Button,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { Suspense, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import z from "zod";

import { VariableMappingSection } from "../components/variable-mapping";
import { useContinuousEvalVariableMapping } from "../hooks/useContinuousEvalVariableMapping";
import { useCreateContinuousEval } from "../hooks/useCreateContinuousEval";

import { EvaluatorSelector } from "./components/EvaluatorSelector";
import { ContinuousEvalWithTracePage } from "./ContinuousEvalWithTracePage";

import { useEval } from "@/components/evaluators/hooks/useEval";
import { useCreateTransformMutation } from "@/components/transforms/hooks/useCreateTransformMutation";
import { useTransforms } from "@/components/transforms/hooks/useTransforms";
import TransformFormModal from "@/components/transforms/TransformFormModal";
import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";
import type { ContinuousEvalResponse, ContinuousEvalTransformVariableMappingRequest } from "@/lib/api-client/api-client";

type EvaluatorFormState = {
  name: ContinuousEvalResponse["llm_eval_name"] | null;
  version: string | null;
};

type TransformFormState = {
  transformId: ContinuousEvalResponse["transform_id"] | null;
};

export const LiveEvalsNew = () => {
  const [searchParams] = useSearchParams();
  const traceId = searchParams.get("traceId");

  if (traceId) {
    return (
      <Suspense
        fallback={
          <Box sx={{ p: 3 }}>
            <Typography>Loading trace...</Typography>
          </Box>
        }
      >
        <ContinuousEvalWithTracePage traceId={traceId} />
      </Suspense>
    );
  }

  return <LiveEvalsNewForm />;
};

const LiveEvalsNewForm = () => {
  const { task } = useTask();
  const [searchParams] = useSearchParams();
  const initialEvalName = searchParams.get("evalName");
  const initialEvalVersion = searchParams.get("evalVersion");

  const navigate = useNavigate();

  const createContinuousEval = useCreateContinuousEval();

  const form = useAppForm({
    defaultValues: {
      name: "",
      description: "",
      enabled: true,
      evaluator: {
        name: initialEvalName ?? null,
        version: initialEvalVersion ?? null,
      } as EvaluatorFormState,
      transform: {
        transformId: null,
      } as TransformFormState,
      variableMappings: [] as ContinuousEvalTransformVariableMappingRequest[],
    },
    validators: {
      onMount: z.object({
        name: z.string().min(1, "Name is required"),
        description: z.string(),
        enabled: z.boolean(),
        evaluator: z.object({
          name: z.string().min(1, "Evaluator name is required"),
          version: z.string().min(1, "Evaluator version is required"),
        }),
        transform: z.object({
          transformId: z.string().min(1, "Transform ID is required"),
        }),
        variableMappings: z.array(
          z.object({
            eval_variable: z.string(),
            transform_variable: z.string(),
          })
        ),
      }),
      onChange: z.object({
        name: z.string().min(1, "Name is required"),
        description: z.string(),
        enabled: z.boolean(),
        evaluator: z.object({
          name: z.string().min(1, "Evaluator name is required"),
          version: z.string().min(1, "Evaluator version is required"),
        }),
        transform: z.object({
          transformId: z.string().min(1, "Transform ID is required"),
        }),
        variableMappings: z.array(
          z.object({
            eval_variable: z.string(),
            transform_variable: z.string(),
          })
        ),
      }),
    },
    onSubmit: async ({ value }) => {
      const { id } = await createContinuousEval.mutateAsync({
        name: value.name,
        description: value.description?.trim() || undefined,
        enabled: value.enabled,
        llm_eval_name: value.evaluator.name!,
        llm_eval_version: value.evaluator.version!,
        transform_id: value.transform.transformId!,
        transform_variable_mapping: value.variableMappings,
      });

      navigate(`/tasks/${task?.id}/continuous-evals/${id}`);
    },
  });

  const evaluator = useStore(form.store, (state) => state.values.evaluator);
  const transform = useStore(form.store, (state) => state.values.transform);

  const { eval: evaluatorData } = useEval(task?.id, evaluator.name ?? undefined, evaluator.version ?? undefined);

  const { data: variableMappingData, isLoading: isLoadingVariableMapping } = useContinuousEvalVariableMapping(
    task?.id,
    transform.transformId ?? undefined,
    evaluator.name ?? undefined,
    evaluator.version ?? undefined
  );

  const variableMappings = useStore(form.store, (state) => state.values.variableMappings);

  const handleSelectionChange = () => {
    form.setFieldValue("variableMappings", []);
  };

  const allVariablesMapped =
    !variableMappingData ||
    variableMappingData.eval_variables.length === 0 ||
    variableMappingData.eval_variables.every((evalVar) => variableMappings.some((m) => m.eval_variable === evalVar && m.transform_variable));

  const canShowVariableMapping = evaluator.name && evaluator.version && transform.transformId;

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
      <Stack
        direction="row"
        alignItems="center"
        gap={1}
        sx={{ px: 2, py: 1, borderBottom: 1, borderColor: "divider", backgroundColor: "background.paper" }}
      >
        <Tooltip title="Go back">
          <IconButton onClick={() => navigate(-1)} size="small">
            <ArrowBackIcon />
          </IconButton>
        </Tooltip>
        <Box>
          <Typography variant="h5" color="text.primary" fontWeight="bold">
            New Continuous Eval
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create a new continuous eval to monitor and analyze your model's performance in real-time.
          </Typography>
        </Box>
      </Stack>
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

        <form.Field name="enabled">
          {(field) => (
            <FormControlLabel
              control={<Switch checked={field.state.value} onChange={(e) => field.handleChange(e.target.checked)} />}
              label="Enable continuous eval"
              slotProps={{ typography: { color: "text.primary" } }}
            />
          )}
        </form.Field>

        <Divider sx={{ my: 2 }} />

        <EvaluatorSelector taskId={task?.id ?? ""} form={form} fields="evaluator" onSelectionChange={handleSelectionChange} />

        {evaluatorData && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="body1" color="text.primary" fontWeight="bold" mb={2}>
              Evaluator Instructions
            </Typography>
            <MustacheHighlightedTextField value={evaluatorData?.instructions ?? ""} onChange={() => {}} readOnly size="small" />
          </Paper>
        )}

        <Divider sx={{ my: 2 }} />

        <TransformSelector taskId={task?.id ?? ""} form={form} fields="transform" onSelectionChange={handleSelectionChange} />

        {canShowVariableMapping && (
          <>
            <Divider sx={{ my: 2 }} />
            <VariableMappingSection
              form={form}
              fields={{ variableMappings: "variableMappings" }}
              eval_variables={variableMappingData?.eval_variables ?? []}
              transform_variables={variableMappingData?.transform_variables ?? []}
              matching_variables={variableMappingData?.matching_variables ?? []}
              isLoading={isLoadingVariableMapping}
            />
          </>
        )}
      </Stack>

      <Box sx={{ p: 3, borderTop: 1, borderColor: "divider" }} className="mt-auto w-full">
        <form.Subscribe selector={(state) => [state.canSubmit, state.isDirty, state.isSubmitting]}>
          {([canSubmit, isDirty, isSubmitting]) => (
            <Button
              variant="contained"
              size="large"
              color="primary"
              disabled={!canSubmit || !isDirty || !allVariablesMapped}
              loading={isSubmitting}
              fullWidth
              type="submit"
            >
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
    const nameInputRef = useRef<HTMLInputElement | null>(null);

    useEffect(() => {
      const raf = requestAnimationFrame(() => {
        nameInputRef.current?.focus();
      });
      return () => cancelAnimationFrame(raf);
    }, []);

    return (
      <Stack gap={2}>
        <group.AppField name="name">
          {(field) => (
            <TextField
              inputRef={nameInputRef}
              label="Eval Name"
              type="text"
              fullWidth
              variant="outlined"
              required
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              error={field.state.meta.isTouched && field.state.meta.errors.length > 0}
            />
          )}
        </group.AppField>

        <group.AppField name="description">
          {(field) => (
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
              error={field.state.meta.isTouched && field.state.meta.errors.length > 0}
            />
          )}
        </group.AppField>
      </Stack>
    );
  },
});

export { EvaluatorSelector } from "./components/EvaluatorSelector";

export const TransformSelector = withFieldGroup({
  defaultValues: {
    transformId: null,
  } as TransformFormState,
  props: {} as {
    taskId: string;
    onSelectionChange?: () => void;
  },
  render: function Render({ group, taskId, onSelectionChange }) {
    const [openCreateTransformModal, setOpenCreateTransformModal] = useState(false);
    const transforms = useTransforms(taskId ?? undefined);

    const createTransform = useCreateTransformMutation(taskId, async (data) => {
      await transforms.refetch();

      setOpenCreateTransformModal(false);

      group.setFieldValue("transformId", data.id);
      onSelectionChange?.();
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
              listeners={{
                onChange: () => {
                  onSelectionChange?.();
                },
              }}
            >
              {(field) => {
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
            </group.AppField>
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
