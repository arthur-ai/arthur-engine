import { Dispatch, MutableRefObject, SetStateAction, useCallback, useEffect, useRef, useState } from "react";

import { PromptPlaygroundState } from "../types";
import { serializePlaygroundState } from "../utils/notebookStateUtils";

import { useApi } from "@/hooks/useApi";
import { useNotebook, useSetNotebookStateMutation, useUpdateNotebookMutation } from "@/hooks/useNotebooks";
import { useTask } from "@/hooks/useTask";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";
import { track, EVENT_NAMES } from "@/services/amplitude";

interface UseNotebookAutoSaveArgs {
  notebookId: string | null;
  initialName: string;
  initialBaseline: string;
  state: PromptPlaygroundState;
  experimentConfig: Partial<PromptExperimentDetail> | null;
  /** Shared save-status state — owned by the parent to avoid circular deps with config hook */
  saveStatus: "saved" | "saving" | "unsaved";
  setSaveStatus: Dispatch<SetStateAction<"saved" | "saving" | "unsaved">>;
  hasUnsavedChangesRef: MutableRefObject<boolean>;
}

/**
 * Manages notebook auto-save, change detection, periodic save, and rename.
 * Encapsulates all save-related state and side effects.
 *
 * Note: `saveStatus` / `setSaveStatus` / `hasUnsavedChangesRef` are passed in
 * from the parent so that the sibling `useExperimentConfig` hook can also mark
 * the notebook as dirty without a circular dependency.
 */
export function useNotebookAutoSave({
  notebookId,
  initialName,
  initialBaseline,
  state,
  experimentConfig,
  saveStatus,
  setSaveStatus,
  hasUnsavedChangesRef,
}: UseNotebookAutoSaveArgs) {
  const apiClient = useApi();
  const { task } = useTask();
  const { notebook } = useNotebook(notebookId ?? undefined);
  const setNotebookStateMutation = useSetNotebookStateMutation();
  const updateNotebookMutation = useUpdateNotebookMutation(task?.id);

  // Notebook name state
  const [notebookName, setNotebookName] = useState<string>(initialName);
  const [isRenaming, setIsRenaming] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState<string>("");

  // Save tracking refs
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const periodicSaveIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastSavedStateRef = useRef<string>(initialBaseline);
  const immediateSaveRef = useRef(false);

  // Sync notebook name from server (e.g. rename by another tab)
  useEffect(() => {
    if (notebook?.name && notebook.name !== notebookName) {
      setNotebookName(notebook.name);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notebook?.name]);

  const autoSaveNotebookState = useCallback(
    async (saveTrigger: "auto" | "manual" = "auto") => {
      if (!notebookId || !apiClient) {
        return;
      }

      const serializedState = serializePlaygroundState(state, experimentConfig);
      const currentStateStr = JSON.stringify(serializedState);

      if (currentStateStr === lastSavedStateRef.current) {
        return;
      }

      try {
        setSaveStatus("saving");

        await setNotebookStateMutation.mutateAsync({
          notebookId,
          request: { state: serializedState },
        });

        lastSavedStateRef.current = currentStateStr;
        hasUnsavedChangesRef.current = false;
        setSaveStatus("saved");

        track(EVENT_NAMES.NOTEBOOK_SAVED, {
          notebook_id: notebookId,
          prompt_count: state.prompts.length,
          save_trigger: saveTrigger,
        });
      } catch (error) {
        console.error("Failed to save notebook state:", error);
        setSaveStatus("unsaved");
      }
    },
    [notebookId, apiClient, state, experimentConfig, setNotebookStateMutation, setSaveStatus, hasUnsavedChangesRef]
  );

  useEffect(() => {
    if (!notebookId || !lastSavedStateRef.current) {
      return;
    }

    const currentStateStr = JSON.stringify(serializePlaygroundState(state, experimentConfig));

    if (currentStateStr !== lastSavedStateRef.current) {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }

      if (immediateSaveRef.current) {
        immediateSaveRef.current = false;
        autoSaveNotebookState();
      } else {
        hasUnsavedChangesRef.current = true;
        setSaveStatus("unsaved");

        autoSaveTimeoutRef.current = setTimeout(() => {
          autoSaveNotebookState();
        }, 5000);
      }
    }

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [state, experimentConfig, notebookId, autoSaveNotebookState, setSaveStatus, hasUnsavedChangesRef]);

  useEffect(() => {
    if (!notebookId) {
      return;
    }

    periodicSaveIntervalRef.current = setInterval(() => {
      if (hasUnsavedChangesRef.current) {
        autoSaveNotebookState();
      }
    }, 10000);

    return () => {
      if (periodicSaveIntervalRef.current) {
        clearInterval(periodicSaveIntervalRef.current);
      }
    };
  }, [notebookId, autoSaveNotebookState, hasUnsavedChangesRef]);

  const requestImmediateSave = useCallback(() => {
    immediateSaveRef.current = true;
  }, []);

  const handleStartRename = useCallback(() => {
    setNewNotebookName(notebookName);
    setIsRenaming(true);
  }, [notebookName]);

  const handleCancelRename = useCallback(() => {
    setIsRenaming(false);
    setNewNotebookName("");
  }, []);

  const handleSaveRename = useCallback(async () => {
    if (!notebookId || !newNotebookName.trim()) {
      return;
    }

    try {
      await updateNotebookMutation.mutateAsync({
        notebookId,
        request: { name: newNotebookName.trim(), description: notebook?.description },
      });
      setNotebookName(newNotebookName.trim());
      setIsRenaming(false);
      setNewNotebookName("");

      track(EVENT_NAMES.NOTEBOOK_RENAMED, {
        notebook_id: notebookId,
      });
    } catch (error) {
      console.error("Failed to rename notebook:", error);
    }
  }, [notebookId, newNotebookName, updateNotebookMutation, notebook?.description]);

  return {
    saveStatus,
    notebookName,
    isRenaming,
    newNotebookName,
    setNewNotebookName,
    autoSaveNotebookState,
    requestImmediateSave,
    handleStartRename,
    handleCancelRename,
    handleSaveRename,
  };
}
