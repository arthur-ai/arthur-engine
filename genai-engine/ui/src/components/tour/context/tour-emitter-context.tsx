import type { Emitter } from "mitt";
import { createContext, useContext } from "react";

import type { AnyTourEvents } from "@/tours/types";

export const TourEmitterContext = createContext<Emitter<AnyTourEvents> | null>(null);

export function useTourEmitter<Events extends AnyTourEvents = AnyTourEvents>(): Emitter<Events> | null {
  const emitter = useContext(TourEmitterContext);
  return emitter as Emitter<Events> | null;
}
