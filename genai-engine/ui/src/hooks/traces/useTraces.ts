import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";

import { queryKeys } from "@/lib/queryKeys";
import { getFilteredTraces, GetFilteredTracesParams } from "@/services/tracing";

export const useTraces = (params: GetFilteredTracesParams) => {
  const api = useApi()!;

  return useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.traces.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredTraces(api, params),
  });
};
