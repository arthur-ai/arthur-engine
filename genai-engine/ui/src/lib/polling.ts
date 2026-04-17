/** Standard polling intervals in milliseconds */
export const POLL_INTERVAL = {
  FAST: 1000,
  DEFAULT: 3000,
  SLOW: 5000,
} as const;

/** Terminal states that indicate processing is complete */
const FINAL_STATES = new Set(["completed", "failed", "passed", "skipped", "error", "partial_failure"]);

/**
 * Checks if a status indicates work is still in progress.
 */
export function isInProgressStatus(status: string | undefined | null): boolean {
  if (!status) return false;
  return !FINAL_STATES.has(status);
}

/**
 * Creates a refetchInterval function for polling a single entity.
 * Polls while the entity's status is in progress, stops when complete/failed.
 */
export function pollWhileInProgress<TData>(
  getStatus: (data: TData | undefined) => string | undefined | null,
  interval: number = POLL_INTERVAL.DEFAULT
) {
  return (query: { state: { data: TData | undefined } }) => {
    return isInProgressStatus(getStatus(query.state.data)) ? interval : false;
  };
}

/**
 * Creates a refetchInterval function for polling a list of entities.
 * Polls while any entity's status is in progress, stops when all are complete/failed.
 */
export function pollWhileAnyInProgress<TData, TItem>(
  getItems: (data: TData | undefined) => TItem[] | undefined | null,
  getStatus: (item: TItem) => string | undefined | null,
  interval: number = POLL_INTERVAL.DEFAULT
) {
  return (query: { state: { data: TData | undefined } }) => {
    const items = getItems(query.state.data);
    if (!items?.length) return false;
    return items.some((item) => isInProgressStatus(getStatus(item))) ? interval : false;
  };
}
