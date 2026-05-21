import { createTourEngine } from "./engine";
import type { TourEngine, TourEngineOptions } from "./engine";

/**
 * Public factory. Aliases `createTourEngine` for ergonomics — most consumers
 * won't think of the engine internals; they just want a tour.
 */
export function createTour(options: TourEngineOptions): TourEngine {
  return createTourEngine(options);
}

export type { TourEngine, TourEngineOptions } from "./engine";
