import { parseAsStringEnum, useQueryState } from "nuqs";
import { useNavigate } from "react-router-dom";

import { LandingHero } from "../landing-hero";
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

  return screen === "form" ? (
    <TryItOutForm onBack={() => setScreen("landing")} onSubmit={handleSubmit} />
  ) : (
    <LandingHero onTry={handleTry} onLogin={handleLogin} />
  );
};
