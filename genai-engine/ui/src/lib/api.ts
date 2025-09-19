import { Api } from "./api-client/api-client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:8000");

export interface ApiClientConfig {
  baseURL?: string;
  token?: string;
}

/**
 * Creates a configured API client instance
 * @param config Configuration options for the API client
 * @returns Configured Api instance
 */
export function createApiClient(config: ApiClientConfig = {}): Api<unknown> {
  const { baseURL = API_BASE_URL, token } = config;

  return new Api({
    baseURL,
    securityWorker: (securityToken) => {
      const authToken = token || securityToken;
      return authToken
        ? { headers: { Authorization: `Bearer ${authToken}` } }
        : {};
    },
  });
}

/**
 * Creates an API client with a specific token
 * @param token The authentication token
 * @param baseURL Optional base URL override
 * @returns Configured Api instance with the provided token
 */
export function createAuthenticatedApiClient(
  token: string,
  baseURL?: string
): Api<unknown> {
  return createApiClient({ baseURL, token });
}

// Export the base API class for advanced usage
export { Api } from "./api-client/api-client";

// Export commonly used types
export type {
  TaskResponse,
  SearchTasksRequest,
  SearchTasksResponse,
  NewTaskRequest,
  RuleResponse,
  MetricResponse,
} from "./api-client/api-client";
