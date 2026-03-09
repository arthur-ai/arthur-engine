import { CircularProgress, Dialog, DialogTitle, Step, StepLabel, Stepper } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useSnackbar } from "notistack";
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import { EvalsStep } from "./components/evals-step";
import { InfoStep } from "./components/info-step";
import { PromptStep } from "./components/prompt-step";
import { createExperimentModalFormOpts, CreateExperimentModalFormValues } from "./form";
import { DeepPartial, deepMerge, formDataToRequest, templateToFormData } from "./utils";

import { ConfirmationModal } from "@/components/common/ConfirmationModal";
import { useAppForm } from "@/components/traces/components/filtering/hooks/form";
import { useCreateExperiment, usePromptExperiment } from "@/hooks/usePromptExperiments";
import { useTask } from "@/hooks/useTask";
import { PromptExperimentDetail } from "@/lib/api-client/api-client";

type Props = {
  templateId?: string;
  initialData?: DeepPartial<CreateExperimentModalFormValues>;
  open: boolean;
  onClose: () => void;
};

export const CreateExperimentModal = ({ templateId, initialData, open, onClose }: Props) => {
  const { experiment, isLoading } = usePromptExperiment(templateId);

  return (
    <Dialog open={open} maxWidth="md" fullWidth aria-labelledby="create-experiment-dialog-title">
      <DialogTitle id="create-experiment-dialog-title">Create Experiment</DialogTitle>
      {isLoading ? <CircularProgress /> : <CreateExperimentModalInner template={experiment} initialData={initialData} onClose={onClose} />}
    </Dialog>
  );
};

const CreateExperimentModalInner = ({
  template,
  initialData,
  onClose,
}: {
  template?: PromptExperimentDetail;
  initialData?: DeepPartial<CreateExperimentModalFormValues>;
  onClose: () => void;
}) => {
  const { task } = useTask()!;
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();

  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);

  const createExperiment = useCreateExperiment(task!.id, {
    onSuccess: (data) => {
      enqueueSnackbar(`Experiment "${data.name}" created successfully!`, { variant: "success" });
      navigate(`/tasks/${task!.id}/prompt-experiments/${data.id}`);
      onClose();
    },
  });

  const defaultValues = (() => {
    const base = template ? templateToFormData(template) : createExperimentModalFormOpts.defaultValues;
    return initialData ? deepMerge(base, initialData) : base;
  })();

  const form = useAppForm({
    ...createExperimentModalFormOpts,
    defaultValues,
    onSubmit: async ({ value, formApi }) => {
      if (value.section === "info") {
        return formApi.setFieldValue("section", "prompts");
      }
      if (value.section === "prompts") {
        return formApi.setFieldValue("section", "evals");
      }

      const request = formDataToRequest(value);

      await createExperiment.mutateAsync(request);
    },
  });

  const handleCancel = useCallback(() => {
    if (form.state.isDirty) {
      setShowDiscardConfirm(true);
    } else {
      onClose();
    }
  }, [form.state.isDirty, onClose]);

  const section = useStore(form.store, (state) => state.values.section);

  const step = {
    info: 0,
    prompts: 1,
    evals: 2,
  }[section];

  return (
    <>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          e.stopPropagation();
          form.handleSubmit();
        }}
        className="contents"
      >
        <Stepper activeStep={step} sx={{ p: 2 }}>
          <Step>
            <StepLabel>Experiment Info</StepLabel>
          </Step>
          <Step>
            <StepLabel>Configure Prompts</StepLabel>
          </Step>
          <Step>
            <StepLabel>Configure Evals</StepLabel>
          </Step>
        </Stepper>
        {section === "info" && <InfoStep form={form} onCancel={handleCancel} />}
        {section === "prompts" && <PromptStep form={form} onCancel={handleCancel} />}
        {section === "evals" && <EvalsStep form={form} onCancel={handleCancel} />}
      </form>
      <ConfirmationModal
        open={showDiscardConfirm}
        onClose={() => setShowDiscardConfirm(false)}
        onConfirm={onClose}
        title="Discard changes?"
        message="You have unsaved changes. Are you sure you want to close this form? Your changes will be lost."
        confirmText="Discard"
        cancelText="Keep editing"
      />
    </>
  );
};
