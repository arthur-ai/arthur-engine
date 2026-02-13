import { ReactNode, createContext, useContext } from "react";

import { PromptPlaygroundState, PromptAction } from "./types";

import type { ModelProvider, PromptExperimentDetail } from "@/lib/api-client/api-client";

interface PromptProviderProps {
  children: ReactNode;
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
  enabledProviders: ModelProvider[];
  availableModels: Map<ModelProvider, string[]>;
  experimentConfig?: Partial<PromptExperimentDetail> | null;
  handleRunSingleWithConfig?: (promptId: string) => Promise<void>;
  isRunningExperiment?: boolean;
  runningExperimentId?: string | null;
  lastCompletedExperimentId?: string | null;
}

const PromptContext = createContext<{
  state: PromptPlaygroundState;
  dispatch: (action: PromptAction) => void;
  enabledProviders: ModelProvider[];
  availableModels: Map<ModelProvider, string[]>;
  experimentConfig?: Partial<PromptExperimentDetail> | null;
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
  enabledProviders,
  availableModels,
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
        enabledProviders,
        availableModels,
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
