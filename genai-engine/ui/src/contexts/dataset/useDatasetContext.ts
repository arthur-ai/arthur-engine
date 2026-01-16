import { useContext, useMemo } from "react";

import { DatasetContext } from "./DatasetContext";
import type { DatasetContextValue, DatasetState } from "./types";

export function useDatasetContext(): DatasetContextValue {
  const context = useContext(DatasetContext);

  if (!context) {
    throw new Error("useDatasetContext must be used within a DatasetContextProvider");
  }

  return context;
}

export function useDatasetSelector<T>(selector: (state: DatasetState) => T): T {
  const { state } = useDatasetContext();
  return useMemo(() => selector(state), [state, selector]);
}

export function useDatasetDispatch(): React.Dispatch<import("./types").DatasetAction> {
  const { dispatch } = useDatasetContext();
  return dispatch;
}

export function useDatasetQueries() {
  const { queries } = useDatasetContext();
  return queries;
}

export function useDatasetMutations() {
  const { mutations } = useDatasetContext();
  return mutations;
}
