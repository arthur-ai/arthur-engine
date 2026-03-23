import { isAxiosError } from "axios";

/**
 * Extracts a user-friendly error message from an API error response.
 * Handles various error formats including:
 * - Axios errors with detail field (string or validation error array)
 * - Standard Error objects
 * - Unknown error types
 *
 * @param error - The error object to extract message from
 * @param fallbackMessage - Default message if extraction fails
 * @returns A user-friendly error message string
 */
export function getApiErrorMessage(error: unknown, fallbackMessage: string = "An error occurred"): string {
  // Handle Axios errors with response data
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (detail) {
      // Handle string detail (most common)
      if (typeof detail === "string") {
        return detail;
      }

      // Handle validation error array: [{ msg: "...", loc: [...], type: "..." }]
      if (Array.isArray(detail) && detail.length > 0) {
        return detail.map((err: { msg?: string; message?: string }) => err.msg || err.message || JSON.stringify(err)).join(", ");
      }

      // Handle object with message property
      if (typeof detail === "object" && detail !== null) {
        const detailObj = detail as { message?: string; msg?: string };
        if (detailObj.message) return detailObj.message;
        if (detailObj.msg) return detailObj.msg;
      }
    }

    // Fall back to Axios error message
    if (error.message) {
      return error.message;
    }
  }

  // Handle standard Error objects
  if (error instanceof Error) {
    return error.message;
  }

  // Handle string errors
  if (typeof error === "string") {
    return error;
  }

  return fallbackMessage;
}
