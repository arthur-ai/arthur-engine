import { useTourStore } from "./useTour";

/**
 * Returns the z-index registered under `name` in the engine's layer slice.
 * Defaults to `fallback` (or `1500` if none provided) when the layer is
 * unknown.
 */
export function useTourLayer(name: string, fallback?: number): number {
  return useTourStore((s) => s.layers[name] ?? fallback ?? 1500);
}
