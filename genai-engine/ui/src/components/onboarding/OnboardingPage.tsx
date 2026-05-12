import { ThemeProvider } from "@mui/material/styles";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { LandingHero } from "./LandingHero";
import { TryItOutForm, type TryItOutSubmission } from "./TryItOutForm";

import { lightTheme } from "@/theme/mui-theme";

type Screen = "landing" | "form";

export const OnboardingPage: React.FC = () => {
  const [screen, setScreen] = useState<Screen>("landing");
  const navigate = useNavigate();

  const handleSubmit = (data: TryItOutSubmission) => {
    // No API calls yet — capture submission for follow-up wiring.
    console.log("Onboarding submission", data);
  };

  return (
    <ThemeProvider theme={lightTheme}>
      {screen === "form" ? (
        <TryItOutForm onBack={() => setScreen("landing")} onSubmit={handleSubmit} />
      ) : (
        <LandingHero onTry={() => setScreen("form")} onLogin={() => navigate("/login")} />
      )}
    </ThemeProvider>
  );
};
