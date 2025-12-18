import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export interface WelcomeState {
  apiKeyClicked: boolean;
  taskIdCopied: boolean;
  dismissed: boolean;

  setApiKeyClicked: (clicked: boolean) => void;
  setTaskIdCopied: (copied: boolean) => void;
  setDismissed: (dismissed: boolean) => void;
  reset: () => void;
}

const initialState = {
  apiKeyClicked: false,
  taskIdCopied: false,
  dismissed: false,
};

export const createWelcomeStore = (taskId: string) =>
  create<WelcomeState>()(
    devtools(
      persist(
        (set) => ({
          ...initialState,

          setApiKeyClicked: (clicked) => {
            set({ apiKeyClicked: clicked }, false, "welcome/setApiKeyClicked");
          },

          setTaskIdCopied: (copied) => {
            set({ taskIdCopied: copied }, false, "welcome/setTaskIdCopied");
          },

          setDismissed: (dismissed) => {
            set({ dismissed }, false, "welcome/setDismissed");
          },

          reset: () => {
            set(initialState, false, "welcome/reset");
          },
        }),
        {
          name: `traces-welcome-${taskId}`, // Unique key per task
        }
      ),
      { name: "welcome-store" }
    )
  );

// Store cache to maintain same store instance per taskId
const storeCache = new Map<string, ReturnType<typeof createWelcomeStore>>();

export const useWelcomeStore = (taskId: string) => {
  if (!storeCache.has(taskId)) {
    storeCache.set(taskId, createWelcomeStore(taskId));
  }
  return storeCache.get(taskId)!;
};
