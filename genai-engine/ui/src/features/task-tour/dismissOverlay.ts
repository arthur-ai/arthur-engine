/**
 * Registry-free dismissal of whatever overlay an element belongs to, using the
 * gestures MUI / Base UI components honor out of the box: a synthetic Escape
 * keydown (the intended close path — it runs the component's own `onClose`, so
 * any cleanup like clearing URL state or showing a discard confirm still fires)
 * plus a backdrop click for surfaces that close on outside-press but not Escape.
 *
 * This is what lets the tour close modals/drawers/popovers it never registered,
 * so presentational components don't have to know the tour exists. Surfaces
 * that opt out of both gestures (`disableEscapeKeyDown` + no backdrop) simply
 * aren't dismissed — the occlusion "bring this into view" affordance stays as
 * the visible fallback. Surfaces needing precise control (e.g. the URL-driven
 * trace drawer) are still handled by the explicit occluder registry instead.
 */

/** MUI + Base UI overlay container conventions. The occluding element is usually deep inside one of these. */
const OVERLAY_CONTAINER_SELECTOR = '.MuiModal-root, .MuiDrawer-root, .MuiPopover-root, .base-Popup-root, [role="dialog"], [role="presentation"]';
const MODAL_ROOT_SELECTOR = ".MuiModal-root, .MuiDrawer-root";

/**
 * Best-effort dismiss of the overlay containing `element`. Returns true when a
 * dismissible overlay container was found and gestures were dispatched (not a
 * guarantee it closed — a surface may ignore them).
 */
export function dismissOverlay(element: Element | null): boolean {
  if (!element || typeof document === "undefined") return false;
  const container = element.closest(OVERLAY_CONTAINER_SELECTOR);
  if (!container) return false;

  // 1. Synthetic Escape — bubbles to the component's keydown handler (the same
  //    path testing-library's `fireEvent.keyDown(dialog, {key:"Escape"})` uses
  //    to close MUI dialogs), triggering its real onClose.
  container.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", bubbles: true, cancelable: true }));

  // 2. Backdrop click fallback for overlays that close on outside-press only.
  const modalRoot = container.matches(MODAL_ROOT_SELECTOR) ? container : container.closest(MODAL_ROOT_SELECTOR);
  const backdrop = modalRoot?.querySelector(":scope > .MuiBackdrop-root");
  if (backdrop instanceof HTMLElement) backdrop.click();

  return true;
}
