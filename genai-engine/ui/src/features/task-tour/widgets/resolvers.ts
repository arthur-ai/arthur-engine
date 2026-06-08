import { tourSelector, type TourId } from "../selectors";

/**
 * Shared `data-tour-id` resolver factories used by the Target widgets to back
 * `queryHook` targets. Centralized here so the "prefer the live surface, fall
 * back to the trigger" pattern isn't copy-pasted (and re-typed) per widget.
 *
 * Bespoke resolvers (DOM walking, accessible-text matching, newest-card
 * selection) stay in their owning widget — only these one-liners are shared.
 */

/**
 * Resolve `preferredId`, falling back to `fallbackId` when the preferred
 * surface (an opened modal/drawer/popover) isn't mounted yet — so the spotlight
 * starts on the trigger and snaps to the surface once it appears.
 */
export function makePreferredDataTourIdResolver(preferredId: TourId, fallbackId: TourId): () => Element | null {
  return () => document.querySelector(tourSelector(preferredId)) ?? document.querySelector(tourSelector(fallbackId));
}

/** Resolve a single `data-tour-id`. */
export function makeDataTourIdResolver(id: TourId): () => Element | null {
  return () => document.querySelector(tourSelector(id));
}
