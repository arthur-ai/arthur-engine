import { queryOptions, useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { Api } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

export const useAnnotation = (annotationId?: string) => {
  const api = useApi()!;

  return useQuery({
    enabled: !!annotationId,
    ...annotationQueryOptions({
      api,
      annotationId: annotationId!,
    }),
  });
};

export const annotationQueryOptions = ({ api, annotationId }: { api: Api<unknown>; annotationId: string }) => {
  return queryOptions({
    queryKey: [queryKeys.annotations.byId(annotationId)],
    queryFn: () => api.api.getAnnotationByIdApiV1TracesAnnotationsAnnotationIdGet(annotationId),
    select: (data) => data.data,
  });
};
