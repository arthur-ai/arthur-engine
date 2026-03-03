import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useId } from "react";

import { useContinuousEval } from "../../hooks/useContinuousEval";
import { useContinuousEvalVariableMapping } from "../../hooks/useContinuousEvalVariableMapping";
import { useUpdateContinuousEval } from "../../hooks/useUpdateContinuousEval";
import { DetailsFieldGroup, EvaluatorSelector, TransformSelector } from "../../new";
import { VariableMappingSection } from "../variable-mapping";

import { CopyableChip } from "@/components/common";
import { useAppForm } from "@arthur/shared-components";
import type { ContinuousEvalResponse, ContinuousEvalTransformVariableMappingRequest } from "@/lib/api-client/api-client";

type Props = {
  continuousEvalId?: string;
  onClose: () => void;
};

export const EditFormDialog = ({ continuousEvalId, onClose }: Props) => {
  const query = useContinuousEval(continuousEvalId);

  return (
    <Dialog open={!!continuousEvalId} onClose={onClose} fullWidth maxWidth="md">
      {query.isLoading ? (
        <DialogContent>
          <CircularProgress size="small" />
        </DialogContent>
      ) : query.data ? (
        <EditForm data={query.data} onClose={onClose} />
      ) : null}
    </Dialog>
  );
};

const EditForm = ({ data, onClose }: { data: ContinuousEvalResponse; onClose: () => void }) => {
  const id = useId();
  const updateContinuousEval = useUpdateContinuousEval(data.id);

  const initialMappings: ContinuousEvalTransformVariableMappingRequest[] =
    data.transform_variable_mapping?.map((m) => ({
      eval_variable: m.eval_variable,
      transform_variable: m.transform_variable,
    })) ?? [];

  const form = useAppForm({
    defaultValues: {
      name: data.name,
      description: data.description ?? "",
      enabled: data.enabled,
      transform: {
        transformId: data.transform_id,
      },
      evaluator: {
        name: data.llm_eval_name,
        version: data.llm_eval_version.toString(),
      },
      variableMappings: initialMappings,
    },
    defaultState: {
      isDirty: true,
    },
    onSubmit: async ({ value }) => {
      await updateContinuousEval.mutateAsync({
        name: value.name,
        description: value.description?.trim() || undefined,
        enabled: value.enabled,
        transform_id: value.transform.transformId,
        llm_eval_name: value.evaluator.name,
        llm_eval_version: value.evaluator.version,
        transform_variable_mapping: value.variableMappings,
      });

      onClose();
    },
  });

  const evaluator = useStore(form.store, (state) => state.values.evaluator);
  const transform = useStore(form.store, (state) => state.values.transform);

  const { data: variableMappingData, isLoading: isLoadingVariableMapping } = useContinuousEvalVariableMapping(
    data.task_id,
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
      <DialogTitle component={Stack} direction="row" alignItems="center" gap={2}>
        <Typography variant="h6" color="text.primary" fontWeight="bold">
          Edit {data.name}
        </Typography>
        <CopyableChip label={data.id} sx={{ fontFamily: "monospace" }} />
      </DialogTitle>
      <DialogContent>
        <Stack
          component="form"
          id={id}
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
          <EvaluatorSelector form={form} fields="evaluator" taskId={data.task_id} onSelectionChange={handleSelectionChange} />
          <Divider sx={{ my: 2 }} />
          <TransformSelector form={form} fields="transform" taskId={data.task_id} onSelectionChange={handleSelectionChange} />
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
        <form.Subscribe selector={(state) => [state.isDirty, state.isSubmitting, state.canSubmit]}>
          {([isDirty, isSubmitting, canSubmit]) => (
            <Button type="submit" form={id} disabled={!canSubmit || !isDirty || !allVariablesMapped} loading={isSubmitting}>
              Save
            </Button>
          )}
        </form.Subscribe>
      </DialogActions>
    </>
  );
};
