import type { Emitter } from "mitt";
import { createContext, useContext } from "react";

import type { AnyTourEvents } from "@/tours/types";

export const TourEmitterContext = createContext<Emitter<AnyTourEvents> | null>(null);

export function useTourEmitter<Events extends AnyTourEvents = AnyTourEvents>(): Emitter<Events> {
  const emitter = useContext(TourEmitterContext);

  if (!emitter) {
    throw new Error("useTourEmitter must be used within TourProvider");
  }

  return emitter as Emitter<Events>;
}
