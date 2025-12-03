import { queryKeys } from "@/lib/queryKeys";
import { getTrace } from "@/services/tracing";
import { useQuery } from "@tanstack/react-query";
import { useApi } from "./useApi";

export const useTrace = (traceId: string) => {
  const api = useApi()!;

  return useQuery({
    queryKey: queryKeys.traces.byId(traceId),
    queryFn: () => getTrace(api, { traceId }),
  });
};
