import { ReactNode, createContext, useContext } from "react";

import { PromptPlaygroundState, PromptAction } from "./types";

interface PromptProviderProps {
  children: ReactNode;
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
}

const PromptContext = createContext<{
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
} | null>(null);

export const usePromptContext = () => {
  const context = useContext(PromptContext);
  if (!context) throw new Error("usePromptContext must be used within PromptProvider");
  return context;
};

export const PromptProvider = ({ children, state, dispatch }: PromptProviderProps) => {
  return <PromptContext.Provider value={{ state, dispatch }}>{children}</PromptContext.Provider>;
};
