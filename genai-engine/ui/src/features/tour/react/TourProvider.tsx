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
 * Wires a tour engine into React. The engine itself is the source of truth
 * (engine state, layer tokens, registries) — this provider only exposes it
 * via context and keeps the navigator in sync.
 *
 * Unlike v0, the provider does NOT inject any plugins or widgets — widgets
 * are ad-hoc consumer components composed inside `<TourHost>`.
 */
export function TourProvider({ tour, navigator, children }: TourProviderProps) {
  useEffect(() => {
    tour.setNavigator(navigator ?? null);
  }, [tour, navigator]);

  return <TourEngineContext.Provider value={tour}>{children}</TourEngineContext.Provider>;
}
