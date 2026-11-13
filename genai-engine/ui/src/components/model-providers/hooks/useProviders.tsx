import { queryOptions, useQuery } from "@tanstack/react-query";

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
    // ScaleDown leads the list; the rest keep the API's order.
    select: (data) => [...data.providers].sort((a, b) => Number(b.provider === "scaledown") - Number(a.provider === "scaledown")),
  });

export const useProviders = () => {
  const api = useApi()!;

  return useQuery(providersQueryOptions({ api }));
};
