import { createContext, ReactNode, useContext } from "react";

import { useEngineConfig } from "@/hooks/useEngineConfig";

interface EngineConfigContextValue {
  demoMode: boolean;
  isLoading: boolean;
}

const EngineConfigContext = createContext<EngineConfigContextValue>({
  demoMode: false,
  isLoading: true,
});

export function EngineConfigProvider({ children }: { children: ReactNode }) {
  const config = useEngineConfig();
  return <EngineConfigContext.Provider value={config}>{children}</EngineConfigContext.Provider>;
}

export function useDemoMode(): EngineConfigContextValue {
  return useContext(EngineConfigContext);
}
