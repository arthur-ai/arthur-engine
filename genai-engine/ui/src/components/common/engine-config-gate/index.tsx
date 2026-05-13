import { ReactNode } from "react";

import { AppLoadingScreen } from "../app-loading-screen";

import { useDemoMode } from "@/contexts/EngineConfigContext";

interface EngineConfigGateProps {
  children: ReactNode;
}

export const EngineConfigGate: React.FC<EngineConfigGateProps> = ({ children }) => {
  const { isLoading } = useDemoMode();
  if (isLoading) return <AppLoadingScreen />;
  return <>{children}</>;
};
