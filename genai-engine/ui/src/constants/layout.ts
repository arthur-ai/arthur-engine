export const TASK_HEADER_HEIGHT = 90;

/**
 * Calculate the available viewport height minus the header
 * Used for full-height scrollable content areas
 */
export const getContentHeight = () => `calc(100vh - ${TASK_HEADER_HEIGHT}px)`;
