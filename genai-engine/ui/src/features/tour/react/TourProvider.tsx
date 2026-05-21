import { useEffect, type ReactNode } from "react";

import type { TourEngine } from "../core/createTour";
import type { TourNavigator } from "../core/types";

import { TourEngineContext } from "./context";

export interface TourProviderProps {
  tour: TourEngine;
  navigator?: TourNavigator | null;
  children: ReactNode;
}

/**
 * Wires a tour engine into React and (optionally) keeps its navigator in sync.
 * The provider does not own engine creation — pass an instance from
 * `createTour({...})`. This makes the engine controllable from anywhere
 * (a Zustand store, a singleton, a per-route hook).
 */
export function TourProvider({ tour, navigator, children }: TourProviderProps) {
  useEffect(() => {
    tour.setNavigator(navigator ?? null);
  }, [tour, navigator]);

  return <TourEngineContext.Provider value={tour}>{children}</TourEngineContext.Provider>;
}
