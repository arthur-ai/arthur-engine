/**
 * Syncs the selected dataset version into the URL while preserving every other
 * param — most importantly the `?row=` deep link managed separately via nuqs.
 */
export function mergeVersionIntoParams(prev: URLSearchParams, selectedVersion: number | undefined): URLSearchParams {
  const next = new URLSearchParams(prev);
  if (selectedVersion !== undefined) {
    next.set("version", selectedVersion.toString());
  } else {
    next.delete("version");
  }
  return next;
}
