import { ReactNode, createContext, useContext } from "react";

import { PromptPlaygroundState, PromptAction } from "./types";

interface PromptProviderProps {
  children: ReactNode;
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
  experimentConfig?: any;
  handleRunSingleWithConfig?: (promptId: string) => Promise<void>;
  isRunningExperiment?: boolean;
  runningExperimentId?: string | null;
  lastCompletedExperimentId?: string | null;
}

const PromptContext = createContext<{
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
  experimentConfig?: any;
  handleRunSingleWithConfig?: (promptId: string) => Promise<void>;
  isRunningExperiment?: boolean;
  runningExperimentId?: string | null;
  lastCompletedExperimentId?: string | null;
} | null>(null);

export const usePromptContext = () => {
  const context = useContext(PromptContext);
  if (!context) throw new Error("usePromptContext must be used within PromptProvider");
  return context;
};

export const PromptProvider = ({
  children,
  state,
  dispatch,
  experimentConfig,
  handleRunSingleWithConfig,
  isRunningExperiment,
  runningExperimentId,
  lastCompletedExperimentId,
}: PromptProviderProps) => {
  return (
    <PromptContext.Provider
      value={{
        state,
        dispatch,
        experimentConfig,
        handleRunSingleWithConfig,
        isRunningExperiment,
        runningExperimentId,
        lastCompletedExperimentId,
      }}
    >
      {children}
    </PromptContext.Provider>
  );
};
