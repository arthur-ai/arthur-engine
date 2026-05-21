import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import { useStartTour } from "@/components/tour/hooks/useStartTour";
import { toursEnabled } from "@/lib/tours-config";
import type { TourId } from "@/tours/registry";
import { tours } from "@/tours/registry";

const isTourId = (value: string): value is TourId => value in tours;

export function TourQueryListener() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { startTour } = useStartTour();
  const handledRef = useRef<string | null>(null);

  useEffect(() => {
    if (!toursEnabled) {
      return;
    }

    const tourParam = searchParams.get("tour");
    if (!tourParam || !isTourId(tourParam)) {
      return;
    }

    if (handledRef.current === tourParam) {
      return;
    }

    const started = startTour(tourParam, { force: true });
    if (started) {
      handledRef.current = tourParam;
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("tour");
      setSearchParams(nextParams, { replace: true });
    }
  }, [searchParams, setSearchParams, startTour]);

  return null;
}
