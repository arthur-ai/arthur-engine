import type { Emitter } from "mitt";
import { useCallback, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { TourEmitterContext } from "@/components/tour/context/tour-emitter-context";
import { TourOrchestrator } from "@/components/tour/engine/orchestrator";
import { trackTourAnalytics } from "@/components/tour/tour-analytics";
import { TourQueryListener } from "@/components/tour/TourQueryListener";
import { toursEnabled } from "@/lib/tours-config";
import { useTourStore } from "@/stores/tour.store";
import { getActiveTour, type TourId } from "@/tours/registry";
import type { AnyTourEvents } from "@/tours/types";

type Props = {
  emitter: Emitter<AnyTourEvents>;
  children: React.ReactNode;
  getRouteParams?: () => Record<string, string>;
};

export function TourProvider({ emitter, children, getRouteParams = () => ({}) }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const orchestratorRef = useRef<TourOrchestrator | null>(null);
  const activeTourKeyRef = useRef<string | null>(null);

  const activeTourId = useTourStore((state) => state.activeTourId);
  const activeStepId = useTourStore((state) => state.activeStepId);
  const setStep = useTourStore((state) => state.actions.setStep);
  const stopTour = useTourStore((state) => state.actions.stopTour);
  const completeTour = useTourStore((state) => state.actions.completeTour);
  const dismissTour = useTourStore((state) => state.actions.dismissTour);

  const getRouteParamsRef = useRef(getRouteParams);
  getRouteParamsRef.current = getRouteParams;

  const initOrchestrator = useCallback(() => {
    if (!toursEnabled) {
      return null;
    }

    if (orchestratorRef.current) {
      return orchestratorRef.current;
    }

    orchestratorRef.current = new TourOrchestrator(
      emitter,
      {
        onStepChange: (stepId) => setStep(stepId),
        onTourComplete: (tourId) => completeTour(tourId),
        onTourDismiss: (tourId) => dismissTour(tourId),
        onTourStop: () => stopTour(),
        onStatusChange: () => {},
        onAnalytics: trackTourAnalytics,
      },
      () => getRouteParamsRef.current()
    );

    return orchestratorRef.current;
  }, [completeTour, dismissTour, emitter, setStep, stopTour]);

  useEffect(() => {
    return () => {
      orchestratorRef.current?.destroy();
      orchestratorRef.current = null;
      activeTourKeyRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!toursEnabled || !activeTourId || !activeStepId) {
      orchestratorRef.current?.stop();
      activeTourKeyRef.current = null;
      return;
    }

    const tour = getActiveTour(activeTourId as TourId);
    if (!tour) {
      stopTour();
      return;
    }

    const orchestrator = initOrchestrator();
    if (!orchestrator) {
      return;
    }

    if (activeTourKeyRef.current !== activeTourId) {
      orchestrator.start(tour, activeStepId);
      activeTourKeyRef.current = activeTourId;
    } else if (orchestrator.getCurrentStep()?.id !== activeStepId) {
      orchestrator.goTo(activeStepId);
    }

    void orchestrator.tick(location.pathname).then((result) => {
      if (result.action === "navigate") {
        navigate(result.route);
      }
    });
  }, [activeStepId, activeTourId, initOrchestrator, location.pathname, navigate, stopTour]);

  if (!toursEnabled) {
    return <>{children}</>;
  }

  return (
    <TourEmitterContext.Provider value={emitter}>
      <TourQueryListener />
      {children}
    </TourEmitterContext.Provider>
  );
}
