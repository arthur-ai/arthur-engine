import { useQuery } from "@tanstack/react-query";

import { useApi } from "../useApi";

import { queryKeys } from "@/lib/queryKeys";

export const useTransform = (id?: string) => {
  const api = useApi()!;

  return useQuery({
    enabled: !!id,
    queryKey: queryKeys.transforms.byId(id!),
    queryFn: () => api.api.getTransformApiV1TracesTransformsTransformIdGet(id!),
    select: (data) => data.data,
  });
};
