import { devtools } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { create } from "zustand/react";

import { PromptExperimentStateConfig } from "../types";

interface ExperimentStoreActions {
  setExperimentConfig: (experimentConfig: PromptExperimentStateConfig) => void;
  setRunningExperimentId: (runningExperimentId: string) => void;
  finishRun: () => void;

  reset: () => void;
}

interface ExperimentStore {
  experimentConfig: PromptExperimentStateConfig | null;
  runningExperimentId: string | null;
  actions: ExperimentStoreActions;
}

export const useExperimentStore = create<ExperimentStore>()(
  devtools(
    immer((set, get) => ({
      experimentConfig: null,
      runningExperimentId: null,
      actions: {
        setExperimentConfig: (experimentConfig: PromptExperimentStateConfig) => {
          set({ experimentConfig }, false, "experiment/setExperimentConfig");
        },

        setRunningExperimentId: (runningExperimentId: string) => {
          set({ runningExperimentId }, false, "experiment/setRunningExperimentId");
        },

        finishRun: () => {
          set({ runningExperimentId: null }, false, "experiment/finishRun");
        },

        reset: () => {
          set({ experimentConfig: null }, false, "experiment/reset");
        },
      },
    }))
  )
);

export const useIsExperimentRunning = () => {
  const runningExperimentId = useExperimentStore((state) => state.runningExperimentId);
  return !!runningExperimentId;
};
