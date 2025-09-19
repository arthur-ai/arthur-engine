import { useMemo } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { createAuthenticatedApiClient, Api } from "@/lib/api";

/**
 * Hook that provides an authenticated API client
 * @returns Configured API client with the current user's token
 */
export function useApi(): Api<any> | null {
  const { token, isAuthenticated } = useAuth();

  return useMemo(() => {
    if (isAuthenticated && token) {
      return createAuthenticatedApiClient(token);
    }
    return null;
  }, [isAuthenticated, token]);
}

/**
 * Hook that provides an API client with a specific token
 * @param token The authentication token to use
 * @returns Configured API client with the provided token
 */
export function useApiWithToken(token: string): Api<any> {
  return useMemo(() => {
    return createAuthenticatedApiClient(token);
  }, [token]);
}
