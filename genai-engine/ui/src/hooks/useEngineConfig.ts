import { useQuery } from "@tanstack/react-query";

import { API_BASE_URL } from "@/lib/api";

interface EngineConfigResponse {
  demo_mode: boolean;
}

export function useEngineConfig() {
  const { data, isPending } = useQuery<EngineConfigResponse>({
    queryKey: ["engine-config"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v2/engine-config`);
      if (!res.ok) throw new Error("Failed to fetch engine config");
      return res.json() as Promise<EngineConfigResponse>;
    },
    staleTime: Infinity,
  });

  return {
    demoMode: data?.demo_mode ?? false,
    isLoading: isPending,
  };
}
