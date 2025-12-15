import { Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Stack, Typography } from "@mui/material";
import { useId } from "react";

import { useContinuousEval } from "../../hooks/useContinuousEval";
import { useUpdateContinuousEval } from "../../hooks/useUpdateContinuousEval";
import { DetailsFieldGroup, EvaluatorSelector, TransformSelector } from "../../new";

import { CopyableChip } from "@/components/common";
import { useAppForm } from "@/components/traces/components/filtering/hooks/form";
import { ContinuousEvalResponse } from "@/lib/api-client/api-client";

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

  const form = useAppForm({
    defaultValues: {
      name: data.name,
      description: data.description ?? "",
      transform: {
        transformId: data.transform_id,
      },
      evaluator: {
        name: data.llm_eval_name,
        version: data.llm_eval_version.toString(),
        variables: {},
      },
    },
    defaultState: {
      isDirty: true,
    },
    onSubmit: async ({ value }) => {
      await updateContinuousEval.mutateAsync({
        name: value.name,
        description: value.description,
        transform_id: value.transform.transformId,
        llm_eval_name: value.evaluator.name,
        llm_eval_version: value.evaluator.version,
      });

      onClose();
    },
  });

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
          </Stack>
          <Divider sx={{ my: 2 }} />
          <EvaluatorSelector form={form} fields="evaluator" taskId={data.task_id} />
          <Divider sx={{ my: 2 }} />
          <TransformSelector form={form} fields="transform" taskId={data.task_id} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <form.Subscribe selector={(state) => [state.isDirty, state.isSubmitting, state.canSubmit]}>
          {([isDirty, isSubmitting, canSubmit]) => (
            <Button type="submit" form={id} disabled={!canSubmit || !isDirty} loading={isSubmitting}>
              Save
            </Button>
          )}
        </form.Subscribe>
      </DialogActions>
    </>
  );
};
