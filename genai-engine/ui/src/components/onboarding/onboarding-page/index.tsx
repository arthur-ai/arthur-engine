import { parseAsStringEnum, useQueryState } from "nuqs";
import { Suspense } from "react";
import { useNavigate } from "react-router-dom";

import { LandingHero } from "../landing-hero";
import { OnboardingContentFallback, OnboardingLayout } from "../onboarding-layout";
import { TryItOutForm, type TryItOutSubmission } from "../try-it-out-form";

import { EVENT_NAMES, track } from "@/services/amplitude";

export const OnboardingPage: React.FC = () => {
  const [screen, setScreen] = useQueryState("screen", parseAsStringEnum(["landing", "form"]).withDefault("landing").withOptions({ history: "push" }));
  const navigate = useNavigate();

  const handleSubmit = (data: TryItOutSubmission) => {
    // No API calls yet — capture submission for follow-up wiring.
    console.log("Onboarding submission", data);
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
