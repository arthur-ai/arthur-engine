import { useCallback, useMemo, useState } from "react";

export interface UseDatasetVersionSelectionReturn {
  selectedVersion: number | undefined;
  currentVersion: number | undefined;
  handleVersionSwitch: (versionNumber: number) => void;
  resetToLatest: () => void;
}

export function useDatasetVersionSelection(
  latestVersion: number | undefined,
  onVersionSwitch?: () => void
): UseDatasetVersionSelectionReturn {
  const [selectedVersion, setSelectedVersion] = useState<number | undefined>(
    undefined
  );

  const currentVersion = useMemo(() => {
    return selectedVersion !== undefined ? selectedVersion : latestVersion;
  }, [selectedVersion, latestVersion]);

  const handleVersionSwitch = useCallback(
    (versionNumber: number) => {
      setSelectedVersion(versionNumber);
      onVersionSwitch?.();
    },
    [onVersionSwitch]
  );

  const resetToLatest = useCallback(() => {
    setSelectedVersion(undefined);
  }, []);

  return {
    selectedVersion,
    currentVersion,
    handleVersionSwitch,
    resetToLatest,
  };
}
