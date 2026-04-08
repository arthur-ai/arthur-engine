import { useAppForm } from "@arthur/shared-components";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider, FormControlLabel, Stack, Switch, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useSnackbar } from "notistack";
import { useId } from "react";
import { useNavigate } from "react-router-dom";
import z from "zod";

import { useContinuousEvalVariableMapping } from "../../hooks/useContinuousEvalVariableMapping";
import { useCreateContinuousEval } from "../../hooks/useCreateContinuousEval";
import { DetailsFieldGroup, EvaluatorSelector, TransformSelector } from "../../new";
import { VariableMappingSection } from "../variable-mapping";

import type { ContinuousEvalTransformVariableMappingRequest } from "@/lib/api-client/api-client";

type Props = {
  open: boolean;
  onClose: () => void;
  taskId: string;
};

export const CreateContinuousEvalDialog = ({ open, onClose, taskId }: Props) => {
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      {open && <CreateForm taskId={taskId} onClose={onClose} />}
    </Dialog>
  );
};

const CreateForm = ({ taskId, onClose }: { taskId: string; onClose: () => void }) => {
  const formId = useId();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const createContinuousEval = useCreateContinuousEval();

  const form = useAppForm({
    defaultValues: {
      name: "",
      description: "",
      enabled: true,
      evaluator: {
        name: null as string | null,
        version: null as string | null,
        eval_type: null as string | null,
      },
      transform: {
        transformId: null as string | null,
      },
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
          eval_type: z.string().min(1, "Evaluator type is required"),
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
          eval_type: z.string().min(1, "Evaluator type is required"),
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
      const isML = value.evaluator.eval_type === "ml";
      const { id } = await createContinuousEval.mutateAsync({
        name: value.name,
        description: value.description?.trim() || undefined,
        enabled: value.enabled,
        eval_type: isML ? "ml_eval" : "llm_eval",
        ...(isML
          ? { ml_eval_name: value.evaluator.name!, ml_eval_version: "latest" }
          : { llm_eval_name: value.evaluator.name!, llm_eval_version: value.evaluator.version! }),
        transform_id: value.transform.transformId!,
        transform_variable_mapping: value.variableMappings,
      });

      enqueueSnackbar("Continuous eval created successfully", { variant: "success" });
      onClose();
      navigate(`/tasks/${taskId}/continuous-evals/${id}`);
    },
  });

  const evaluator = useStore(form.store, (state) => state.values.evaluator);
  const transform = useStore(form.store, (state) => state.values.transform);

  const { data: variableMappingData, isLoading: isLoadingVariableMapping } = useContinuousEvalVariableMapping(
    taskId,
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
    <>
      <DialogTitle>
        <Typography variant="h6" color="text.primary" fontWeight="bold">
          New Continuous Eval
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Create a new continuous eval to monitor and analyze your model's performance in real-time.
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Stack
          component="form"
          id={formId}
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            form.handleSubmit();
          }}
          gap={2}
          sx={{ pt: 1 }}
        >
          <Stack gap={2}>
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
          </Stack>
          <Divider sx={{ my: 2 }} />
          <EvaluatorSelector form={form} fields="evaluator" taskId={taskId} onSelectionChange={handleSelectionChange} />
          <Divider sx={{ my: 2 }} />
          <TransformSelector form={form} fields="transform" taskId={taskId} onSelectionChange={handleSelectionChange} />
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
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <form.Subscribe selector={(state) => [state.canSubmit, state.isDirty, state.isSubmitting]}>
          {([canSubmit, isDirty, isSubmitting]) => (
            <Button type="submit" form={formId} variant="contained" disabled={!canSubmit || !isDirty || !allVariablesMapped} loading={isSubmitting}>
              Create Continuous Eval
            </Button>
          )}
        </form.Subscribe>
      </DialogActions>
    </>
  );
};
