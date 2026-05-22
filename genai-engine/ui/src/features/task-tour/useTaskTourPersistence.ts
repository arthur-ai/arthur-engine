import { useCallback, useEffect, useState } from "react";

import { readTourPersistence, writeTourPersistence, type TourPersistenceStatus } from "@/features/tour";

export const TASK_TOUR_STORAGE_KEY = "arthur:task-tour:status";

interface UseTaskTourPersistenceResult {
  status: TourPersistenceStatus;
  setStatus: (next: TourPersistenceStatus) => void;
  reset: () => void;
}

/**
 * React-side mirror of the persistence plugin's storage. The plugin writes on
 * `tour:start` / `tour:end`; this hook lets the React tree read the same key
 * on mount, force-update on writes from other tabs/windows, and accept manual
 * overrides (e.g. when the certificate dialog is acknowledged).
 */
export function useTaskTourPersistence(storageKey: string = TASK_TOUR_STORAGE_KEY): UseTaskTourPersistenceResult {
  const [status, setStatusState] = useState<TourPersistenceStatus>(() => readTourPersistence(storageKey));

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onStorage = (e: StorageEvent) => {
      if (e.key !== storageKey) return;
      setStatusState(readTourPersistence(storageKey));
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [storageKey]);

  const setStatus = useCallback(
    (next: TourPersistenceStatus) => {
      writeTourPersistence(storageKey, next);
      setStatusState(next);
    },
    [storageKey]
  );

  const reset = useCallback(() => setStatus("unseen"), [setStatus]);

  return { status, setStatus, reset };
}
