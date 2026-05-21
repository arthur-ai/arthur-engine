import { useCallback } from "react";

import { useTourEmitter } from "@/components/tour/context/tour-emitter-context";
import type { AnyTourEvents } from "@/tours/types";

export function useEmitTourEvent<Events extends AnyTourEvents = AnyTourEvents>() {
  const emitter = useTourEmitter<Events>();

  return useCallback(
    <K extends keyof Events & string>(type: K, event: Events[K]) => {
      emitter.emit(type, event);
    },
    [emitter]
  );
}
