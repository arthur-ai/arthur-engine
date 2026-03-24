import { useQuery } from "@tanstack/react-query";

import { useApi } from "@/hooks/useApi";
import { queryKeys } from "@/lib/queryKeys";

export function useTransformVersion(transformId: string | null | undefined, versionId: string | null | undefined) {
  const api = useApi();

  return useQuery({
    queryKey: [...queryKeys.transforms.version(transformId ?? "", versionId ?? ""), api],
    queryFn: async () => {
      const response = await api!.api.getTransformVersionApiV1TracesTransformsTransformIdVersionsVersionIdGet(
        transformId!,
        versionId!
      );
      return response.data;
    },
    enabled: !!api && !!transformId && !!versionId,
    staleTime: 5 * 60 * 1000, // 5 minutes — snapshots are immutable
  });
}
