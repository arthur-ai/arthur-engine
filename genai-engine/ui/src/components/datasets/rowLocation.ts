/**
 * Returns the 0-based table page a row lands on given the full ordered id list,
 * or null when the row isn't in the list (e.g. a stale deep link).
 */
export function computeRowPage(rowIds: string[], rowId: string, rowsPerPage: number): number | null {
  const index = rowIds.indexOf(rowId);
  if (index === -1 || rowsPerPage <= 0) {
    return null;
  }
  return Math.floor(index / rowsPerPage);
}
