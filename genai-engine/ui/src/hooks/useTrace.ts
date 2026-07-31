import { useQuery } from "@tanstack/react-query";

import { useApi } from "./useApi";

import { queryKeys } from "@/lib/queryKeys";
import { getTrace } from "@/services/tracing";

export const useTrace = (traceId: string) => {
  const api = useApi()!;

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  return useQuery({
    queryKey: queryKeys.traces.byId(traceId),
    queryFn: () => getTrace(api, { traceId }),
  });
};
