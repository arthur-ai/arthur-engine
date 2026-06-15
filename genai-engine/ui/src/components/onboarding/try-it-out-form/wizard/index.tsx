import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, Button, Paper, Slide, Step, StepLabel, Stepper, Typography } from "@mui/material";
import { revalidateLogic, useStore } from "@tanstack/react-form";
import { useEffect, useRef, useState } from "react";

import { useAppForm } from "../hooks/form";
import type { TryItOutFormProps } from "../types";

import { STEP_COUNT, STEP_LABELS, STEP_NAMES, type StepIndex, type StepName } from "./options";
import { flattenWizardValues, getInvalidGroupFields, wizardFormOpts, wizardSchema, type WizardValues } from "./schema";
import { TryItOutFormWizardAboutStep } from "./steps/about";
import { TryItOutFormWizardDiscoveryStep } from "./steps/discovery";
import { TryItOutFormWizardIdentityStep } from "./steps/identity";

import { track } from "@/services/analytics";

const VARIANT = "wizard" as const;

export const TryItOutFormWizard: React.FC<TryItOutFormProps> = ({ onBack, onSubmit }) => {
  const [step, setStep] = useState<StepIndex>(0);
  const [transitionDirection, setTransitionDirection] = useState<"left" | "right">("left");
  const formStartedRef = useRef(false);

  const form = useAppForm({
    ...wizardFormOpts,
    validationLogic: revalidateLogic(),
    validators: {
      onDynamic: wizardSchema,
    },
    listeners: {
      onMount: () => {
        track("onboarding/form_viewed", { variant: VARIANT });
      },
      onChange: () => {
        if (!formStartedRef.current) {
          formStartedRef.current = true;
          track("onboarding/form_started", { variant: VARIANT });
        }
      },
    },
    onSubmit: async ({ value }) => {
      const flat = flattenWizardValues(value);
      await onSubmit(flat, { formVariant: VARIANT });
    },
    onSubmitInvalid: ({ formApi }) => {
      const invalidFields = Object.entries(formApi.state.fieldMeta)
        .filter(([, meta]) => (meta?.errors?.length ?? 0) > 0)
        .map(([name]) => name);
      track("onboarding/form_submit_failed", { variant: VARIANT, invalid_fields: invalidFields });
    },
  });

  const isSubmitting = useStore(form.store, (s) => s.isSubmitting);

  useEffect(() => {
    const stepName: StepName = STEP_NAMES[step];
    track("onboarding/wizard_step_viewed", { step: step + 1, step_name: stepName });
  }, [step]);

  const goBack = (currentStep: StepIndex) => {
    if (currentStep === 0) {
      track("onboarding/form_back_clicked", { variant: VARIANT });
      onBack();
      return;
    }
    const target = (currentStep - 1) as StepIndex;
    track("onboarding/wizard_step_back", {
      from_step: currentStep + 1,
      to_step: target + 1,
    });
    setTransitionDirection("right");
    setStep(target);
  };

  const advance = (currentStep: StepIndex) => () => {
    const stepName: StepName = STEP_NAMES[currentStep];
    track("onboarding/wizard_step_completed", {
      step: currentStep + 1,
      step_name: stepName,
    });
    if (currentStep === STEP_COUNT - 1) {
      void form.handleSubmit();
      return;
    }
    setTransitionDirection("left");
    setStep((currentStep + 1) as StepIndex);
  };

  const reportInvalid = (currentStep: StepIndex) => () => {
    const stepName: StepName = STEP_NAMES[currentStep];
    const invalidFields = getInvalidGroupFields(form.state.fieldMeta, stepName as keyof WizardValues);
    track("onboarding/wizard_step_submit_failed", {
      step: currentStep + 1,
      step_name: stepName,
      invalid_fields: invalidFields,
    });
  };

  return (
    <>
      <Button
        onClick={() => goBack(0)}
        startIcon={<ArrowBackIcon sx={{ fontSize: 16 }} />}
        sx={{
          textTransform: "none",
          fontSize: 13,
          fontWeight: 500,
          color: "text.secondary",
          p: 0,
          mb: 2.5,
          minWidth: 0,
          "&:hover": { backgroundColor: "transparent", color: "text.primary" },
        }}
      >
        Back
      </Button>

      <Typography
        component="h1"
        sx={{
          fontSize: 22,
          fontWeight: 700,
          color: "text.primary",
          letterSpacing: "-0.01em",
          lineHeight: 1.25,
          mb: 1,
        }}
      >
        Try Arthur Engine
      </Typography>
      <Typography sx={{ fontSize: 14, color: "text.secondary", lineHeight: 1.55, mb: 3 }}>
        Tell us who you are and we&apos;ll spin up a demo task scoped just to you.
      </Typography>

      <Paper
        elevation={0}
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "12px",
          p: 3.5,
          mt: 1,
          display: "flex",
          flexDirection: "column",
          gap: 2.25,
          overflow: "hidden",
        }}
      >
        <Stepper activeStep={step} alternativeLabel sx={{ mb: 1 }}>
          {STEP_LABELS.map((label, i) => (
            <Step key={label} completed={i < step}>
              <StepLabel slotProps={{ label: { sx: { fontSize: 12 } } }}>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        <Box sx={{ position: "relative", minHeight: 360 }}>
          {step === 0 && (
            <Slide in direction={transitionDirection} mountOnEnter unmountOnExit>
              <Box>
                <TryItOutFormWizardIdentityStep form={form} onBack={() => goBack(0)} onAdvance={advance(0)} onInvalid={reportInvalid(0)} />
              </Box>
            </Slide>
          )}
          {step === 1 && (
            <Slide in direction={transitionDirection} mountOnEnter unmountOnExit>
              <Box>
                <TryItOutFormWizardAboutStep form={form} onBack={() => goBack(1)} onAdvance={advance(1)} onInvalid={reportInvalid(1)} />
              </Box>
            </Slide>
          )}
          {step === 2 && (
            <Slide in direction={transitionDirection} mountOnEnter unmountOnExit>
              <Box>
                <TryItOutFormWizardDiscoveryStep
                  form={form}
                  onBack={() => goBack(2)}
                  onAdvance={advance(2)}
                  onInvalid={reportInvalid(2)}
                  isSubmitting={isSubmitting}
                />
              </Box>
            </Slide>
          )}
        </Box>
      </Paper>
    </>
  );
};
