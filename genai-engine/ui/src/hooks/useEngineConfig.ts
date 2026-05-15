import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { createApiClient } from "@/lib/api";

export function useEngineConfig() {
  const apiClient = useMemo(() => createApiClient(), []);

  const { data, isPending } = useQuery({
    queryKey: ["engine-config"],
    queryFn: () => apiClient.api.getEngineConfigApiV2EngineConfigGet().then((r) => r.data),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  return {
    demoMode: data?.demo_mode ?? false,
    isLoading: isPending,
  };
}
