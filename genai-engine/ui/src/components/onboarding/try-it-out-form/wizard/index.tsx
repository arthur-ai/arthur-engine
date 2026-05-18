import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, Button, Paper, Slide, Step, StepLabel, Stepper, Typography } from "@mui/material";
import { revalidateLogic, useForm, useStore } from "@tanstack/react-form";
import { useEffect, useRef, useState } from "react";

import { EngineTopNav } from "../../engine-top-nav";
import type { TryItOutFormProps } from "../types";

import { STEP_COUNT, STEP_LABELS, STEP_NAMES, type StepIndex, type StepName } from "./options";
import {
  aboutSchema,
  discoverySchema,
  flattenWizardValues,
  getInvalidGroupFields,
  identitySchema,
  wizardDefaultValues,
  wizardSchema,
  type WizardValues,
} from "./schema";
import { TryItOutFormWizardAboutStep } from "./steps/about";
import { TryItOutFormWizardDiscoveryStep } from "./steps/discovery";
import { TryItOutFormWizardIdentityStep } from "./steps/identity";

import { EVENT_NAMES, identify, track } from "@/services/amplitude";

const VARIANT = "wizard" as const;

export const TryItOutFormWizard: React.FC<TryItOutFormProps> = ({ onBack, onSubmit }) => {
  const [step, setStep] = useState<StepIndex>(0);
  const [transitionDirection, setTransitionDirection] = useState<"left" | "right">("left");
  const formStartedRef = useRef(false);

  const form = useForm({
    defaultValues: wizardDefaultValues,
    validationLogic: revalidateLogic(),
    validators: {
      onDynamic: wizardSchema,
    },
    listeners: {
      onMount: () => {
        track(EVENT_NAMES.ONBOARDING_FORM_VIEWED, { variant: VARIANT });
      },
      onChange: () => {
        if (!formStartedRef.current) {
          formStartedRef.current = true;
          track(EVENT_NAMES.ONBOARDING_FORM_STARTED, { variant: VARIANT });
        }
      },
    },
    onSubmit: ({ value }) => {
      const flat = flattenWizardValues(value);
      track(EVENT_NAMES.ONBOARDING_FORM_SUBMITTED, {
        variant: VARIANT,
        maturity: flat.maturity,
        brings: flat.brings,
        bringsOther: flat.bringsOther,
        competitors: flat.competitors,
        competitorOther: flat.competitorOther,
        attribution: flat.attribution,
        attributionOther: flat.attributionOther,
        company: flat.company,
      });
      identify(flat.email, {
        firstName: flat.firstName,
        lastName: flat.lastName,
        email: flat.email,
        jobTitle: flat.jobTitle,
        company: flat.company,
      });
      onSubmit(flat);
    },
    onSubmitInvalid: ({ formApi }) => {
      const invalidFields = Object.entries(formApi.state.fieldMeta)
        .filter(([, meta]) => (meta?.errors?.length ?? 0) > 0)
        .map(([name]) => name);
      track(EVENT_NAMES.ONBOARDING_FORM_SUBMIT_FAILED, { variant: VARIANT, invalid_fields: invalidFields });
    },
  });

  const isSubmitting = useStore(form.store, (s) => s.isSubmitting);

  useEffect(() => {
    const stepName: StepName = STEP_NAMES[step];
    track(EVENT_NAMES.ONBOARDING_WIZARD_STEP_VIEWED, { step: step + 1, step_name: stepName });
  }, [step]);

  const goBack = (currentStep: StepIndex) => {
    if (currentStep === 0) {
      track(EVENT_NAMES.ONBOARDING_FORM_BACK_CLICKED, { variant: VARIANT });
      onBack();
      return;
    }
    const target = (currentStep - 1) as StepIndex;
    track(EVENT_NAMES.ONBOARDING_WIZARD_STEP_BACK, {
      from_step: currentStep + 1,
      to_step: target + 1,
    });
    setTransitionDirection("right");
    setStep(target);
  };

  const handleGroupSubmit = (currentStep: StepIndex) => {
    const stepName: StepName = STEP_NAMES[currentStep];
    track(EVENT_NAMES.ONBOARDING_WIZARD_STEP_COMPLETED, {
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

  const handleGroupSubmitInvalid = (currentStep: StepIndex) => {
    const stepName: StepName = STEP_NAMES[currentStep];
    const invalidFields = getInvalidGroupFields(form.state.fieldMeta, stepName as keyof WizardValues);
    track(EVENT_NAMES.ONBOARDING_WIZARD_STEP_SUBMIT_FAILED, {
      step: currentStep + 1,
      step_name: stepName,
      invalid_fields: invalidFields,
    });
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        backgroundColor: "background.default",
      }}
    >
      <EngineTopNav />
      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "safe center",
          justifyContent: "safe center",
          px: 3,
          py: 4,
          overflowY: "auto",
        }}
      >
        <Box sx={{ width: "100%", maxWidth: 520 }}>
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
                    <form.FormGroup
                      name="identity"
                      validators={{ onDynamic: identitySchema }}
                      onGroupSubmit={() => handleGroupSubmit(0)}
                      onGroupSubmitInvalid={() => handleGroupSubmitInvalid(0)}
                    >
                      {(group) => <TryItOutFormWizardIdentityStep form={form} group={group} onBack={() => goBack(0)} />}
                    </form.FormGroup>
                  </Box>
                </Slide>
              )}
              {step === 1 && (
                <Slide in direction={transitionDirection} mountOnEnter unmountOnExit>
                  <Box>
                    <form.FormGroup
                      name="about"
                      validators={{ onDynamic: aboutSchema }}
                      onGroupSubmit={() => handleGroupSubmit(1)}
                      onGroupSubmitInvalid={() => handleGroupSubmitInvalid(1)}
                    >
                      {(group) => <TryItOutFormWizardAboutStep form={form} group={group} onBack={() => goBack(1)} />}
                    </form.FormGroup>
                  </Box>
                </Slide>
              )}
              {step === 2 && (
                <Slide in direction={transitionDirection} mountOnEnter unmountOnExit>
                  <Box>
                    <form.FormGroup
                      name="discovery"
                      validators={{ onDynamic: discoverySchema }}
                      onGroupSubmit={() => handleGroupSubmit(2)}
                      onGroupSubmitInvalid={() => handleGroupSubmitInvalid(2)}
                    >
                      {(group) => <TryItOutFormWizardDiscoveryStep form={form} group={group} onBack={() => goBack(2)} isSubmitting={isSubmitting} />}
                    </form.FormGroup>
                  </Box>
                </Slide>
              )}
            </Box>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};
