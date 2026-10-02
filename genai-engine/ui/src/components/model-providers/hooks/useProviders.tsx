import { queryOptions, useQuery } from "@tanstack/react-query";

import { getScaleDownProvider, SCALEDOWN } from "../scaledown-demo";

import { useApi } from "@/hooks/useApi";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export const providersQueryOptions = ({ api }: { api: Api<unknown> }) =>
  queryOptions({
    queryKey: queryKeys.providers.all(),
    queryFn: async () => {
      const response = await api.api.getModelProvidersApiV1ModelProvidersGet();
      return response.data;
    },
    // Appended in select, not queryFn: useModelProviders shares this cache entry and
    // must not offer ScaleDown in model pickers while the backend can't call it.
    select: (data) => [...data.providers.filter((p) => p.provider !== SCALEDOWN), getScaleDownProvider()],
  });

export const useProviders = () => {
  const api = useApi()!;

  return useQuery(providersQueryOptions({ api }));
};
