import { Box, Button, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { Suspense, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useCreateOnboardingSubmissionMutation } from "../hooks/useCreateOnboardingSubmissionMutation";
import { LandingHero } from "../landing-hero";
import { OnboardingContentFallback, OnboardingLayout } from "../onboarding-layout";
import { TryItOutForm, type TryItOutSubmission } from "../try-it-out-form";
import type { TryItOutSubmitMeta } from "../try-it-out-form/types";

import { EVENT_NAMES, identify, track } from "@/services/amplitude";

export const OnboardingPage: React.FC = () => {
  const [screen, setScreen] = useQueryState("screen", parseAsStringEnum(["landing", "form"]).withDefault("landing").withOptions({ history: "push" }));
  const [submitSucceeded, setSubmitSucceeded] = useState(false);
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();

  const submitMutation = useCreateOnboardingSubmissionMutation({
    onSuccess: (_response, { data, meta }) => {
      track(EVENT_NAMES.ONBOARDING_FORM_SUBMITTED, {
        variant: meta.formVariant,
        maturity: data.maturity,
        brings: data.brings,
        bringsOther: data.bringsOther,
        competitors: data.competitors,
        competitorOther: data.competitorOther,
        attribution: data.attribution,
        attributionOther: data.attributionOther,
        company: data.company,
      });
      identify(data.email, {
        firstName: data.firstName,
        lastName: data.lastName,
        email: data.email,
        jobTitle: data.jobTitle,
        company: data.company,
      });
      setSubmitSucceeded(true);
    },
    onError: (error, { meta }) => {
      track(EVENT_NAMES.ONBOARDING_FORM_SUBMIT_FAILED, {
        variant: meta.formVariant,
        message: error.message,
      });
      enqueueSnackbar(error.message || "Something went wrong. Please try again.", { variant: "error" });
    },
  });

  const handleSubmit = async (data: TryItOutSubmission, meta: TryItOutSubmitMeta) => {
    await submitMutation.mutateAsync({ data, meta });
  };

  const handleTry = () => {
    track(EVENT_NAMES.ONBOARDING_PATH_SELECTED, { path: "try" });
    void setScreen("form");
  };

  const handleLogin = () => {
    track(EVENT_NAMES.ONBOARDING_PATH_SELECTED, { path: "login" });
    navigate("/login");
  };

  const isLanding = screen === "landing";

  return (
    <OnboardingLayout variant={isLanding ? "landing" : "default"} contentMaxWidth={isLanding ? 880 : 520}>
      {isLanding ? (
        <LandingHero onTry={handleTry} onLogin={handleLogin} />
      ) : submitSucceeded ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography variant="h5" component="h1">
            Thanks — we&apos;ve got your details
          </Typography>
          <Typography variant="body1" color="text.secondary">
            We&apos;ll use this to tailor your Arthur demo experience.
          </Typography>
          <Button variant="contained" onClick={() => navigate("/login")} sx={{ alignSelf: "flex-start", textTransform: "none" }}>
            Continue to sign in
          </Button>
        </Box>
      ) : (
        <Suspense fallback={<OnboardingContentFallback />}>
          <TryItOutForm onBack={() => void setScreen("landing")} onSubmit={handleSubmit} />
        </Suspense>
      )}
    </OnboardingLayout>
  );
};
