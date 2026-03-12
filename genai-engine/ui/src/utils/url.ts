/**
 * Double-encodes a value for use in API path segments. Uvicorn decodes the
 * request path before routing, so single-encoded "/" (%2F) breaks routes.
 * The backend must call decode_path_param() (src/utils/url_encoding.py) to
 * recover the original value. Use plain encodeURIComponent for React Router URLs.
 */
export function encodePathParam(value: string): string {
  return encodeURIComponent(encodeURIComponent(value));
}
