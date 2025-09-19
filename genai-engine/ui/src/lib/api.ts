import { Api } from "./api-client/api-client";
import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:8000");

// Configure axios to serialize array parameters without brackets
axios.defaults.paramsSerializer = {
  serialize: (params: Record<string, unknown>) => {
    const searchParams = new URLSearchParams();
    Object.keys(params).forEach((key) => {
      const value = params[key];
      if (Array.isArray(value)) {
        // Serialize arrays as repeated parameters instead of brackets
        value.forEach((item) => searchParams.append(key, String(item)));
      } else if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });
    return searchParams.toString();
  },
};

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
  QueryTracesWithMetricsResponse,
  TraceResponse,
  NestedSpanWithMetricsResponse,
} from "./api-client/api-client";
