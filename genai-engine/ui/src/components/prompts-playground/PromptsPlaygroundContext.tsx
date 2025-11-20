import { ReactNode, createContext, useContext } from "react";

import { PromptPlaygroundState, PromptAction } from "./types";

interface PromptProviderProps {
  children: ReactNode;
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
  experimentConfig?: any;
}

const PromptContext = createContext<{
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
  experimentConfig?: any;
} | null>(null);

export const usePromptContext = () => {
  const context = useContext(PromptContext);
  if (!context) throw new Error("usePromptContext must be used within PromptProvider");
  return context;
};

export const PromptProvider = ({ children, state, dispatch, experimentConfig }: PromptProviderProps) => {
  return <PromptContext.Provider value={{ state, dispatch, experimentConfig }}>{children}</PromptContext.Provider>;
};
