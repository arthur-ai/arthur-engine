import { createContext } from "react";

import type { TourEngine } from "../core/createTour";

export const TourEngineContext = createContext<TourEngine | null>(null);
