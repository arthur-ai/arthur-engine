import { createTourEngine } from "./engine";
import type { TourEngine, TourEngineOptions } from "./engine";

export function createTour(options: TourEngineOptions): TourEngine {
  return createTourEngine(options);
}

export type { TourEngine, TourEngineOptions } from "./engine";
