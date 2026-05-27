import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef } from "react";

import { createReadFirstTraceFromCache, registerTracesTourPrepDeps } from "../tracesTourPrep";

import { useDrawerTarget } from "@/components/traces/hooks/useDrawerTarget";
import { usePaginationContext } from "@/components/traces/stores/pagination-context";
import { useApi } from "@/hooks/useApi";

export interface TracesTourBridgeProps {
  taskId: string;
}

/**
 * Registers trace-table / trace-drawer side-effect deps with the tour step
 * `onEnter` prep hook (`prepareTracesTourStep`). The prep runs inside the
 * engine after navigation and before spotlight targeting.
 */
export function TracesTourBridge({ taskId }: TracesTourBridgeProps) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [drawerTarget, setDrawerTarget] = useDrawerTarget();
  const drawerTargetRef = useRef(drawerTarget);
  drawerTargetRef.current = drawerTarget;
  const setPaginationContext = usePaginationContext((state) => state.actions.setContext);
  const readFirstTraceFromCache = useMemo(
    () => createReadFirstTraceFromCache((filters) => queryClient.getQueriesData(filters)),
    [queryClient]
  );

  useEffect(() => {
    registerTracesTourPrepDeps({
      taskId,
      api,
      getDrawerTarget: () => ({
        target: drawerTargetRef.current.target,
        id: drawerTargetRef.current.id,
      }),
      setDrawerTarget,
      setPaginationContext,
      readFirstTraceFromCache,
    });
    return () => registerTracesTourPrepDeps(null);
  }, [api, readFirstTraceFromCache, setDrawerTarget, setPaginationContext, taskId]);

  return null;
}
