export const TASK_HEADER_HEIGHT = 90;

/**
 * Calculate the available viewport height minus the header
 * Used for full-height scrollable content areas
 */
export const getContentHeight = () => `calc(100vh - ${TASK_HEADER_HEIGHT}px)`;

/**
 * Width of the in-task left navigation sidebar, in pixels.
 * Single source of truth: the sidebar (`SidebarNavigation`) and any element that
 * must clear it (e.g. `ChatbotDrawer`) both derive from this value.
 * Kept equal to what Tailwind's `w-64` produced (16rem = 256px).
 */
export const SIDEBAR_WIDTH_PX = 256;
