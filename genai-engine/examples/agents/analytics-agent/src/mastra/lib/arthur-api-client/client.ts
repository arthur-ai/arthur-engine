import { Api } from "./api-client";

/**
 * Creates and returns a configured Arthur API client instance
 * using environment variables for authentication
 */
export function getArthurApiClient(): Api<unknown> {
  return new Api<unknown>({
    baseURL: process.env.ARTHUR_BASE_URL,
    headers: {
      Authorization: `Bearer ${process.env.ARTHUR_API_KEY}`,
    },
  });
}
