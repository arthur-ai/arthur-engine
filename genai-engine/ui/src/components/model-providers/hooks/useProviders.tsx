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
    select: (data) => data.providers,
  });

export const useProviders = () => {
  const api = useApi()!;

  return useQuery(providersQueryOptions({ api }));
};
