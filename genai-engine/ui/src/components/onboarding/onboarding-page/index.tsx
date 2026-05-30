import { useSnackbar } from "notistack";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { Suspense } from "react";
import { useNavigate } from "react-router-dom";

import { useCreateOnboardingSubmissionMutation } from "../hooks/useCreateOnboardingSubmissionMutation";
import { LandingHero } from "../landing-hero";
import { OnboardingContentFallback, OnboardingLayout } from "../onboarding-layout";
import { TryItOutForm, type TryItOutSubmission } from "../try-it-out-form";
import type { TryItOutSubmitMeta } from "../try-it-out-form/types";

import { useAuth } from "@/contexts/AuthContext";
import { storeRecipientName } from "@/features/task-tour/recipientName";
import { EVENT_NAMES, identify, track } from "@/services/amplitude";

export const OnboardingPage: React.FC = () => {
  const [screen, setScreen] = useQueryState("screen", parseAsStringEnum(["landing", "form"]).withDefault("landing").withOptions({ history: "push" }));
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { login } = useAuth();

  const submitMutation = useCreateOnboardingSubmissionMutation({
    onSuccess: async (signup, { data, meta }) => {
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

      // Remember the recipient for the tour completion certificate, which renders
      // after the user lands in the app post-signup.
      storeRecipientName(`${data.firstName} ${data.lastName}`);

      const authenticated = await login(signup.api_key);
      if (authenticated) {
        navigate(`/${signup.task_id}/traces`, { replace: true });
        return;
      }

      enqueueSnackbar("Your workspace was created, but sign-in failed. Use your API key on the login page.", {
        variant: "warning",
      });
      navigate("/login", { replace: true });
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
      ) : (
        <Suspense fallback={<OnboardingContentFallback />}>
          <TryItOutForm onBack={() => void setScreen("landing")} onSubmit={handleSubmit} />
        </Suspense>
      )}
    </OnboardingLayout>
  );
};
