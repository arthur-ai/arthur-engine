import type { Emitter } from "mitt";
import { useCallback, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { TourEmitterContext } from "@/components/tour/context/tour-emitter-context";
import { TourOrchestrator } from "@/components/tour/engine/orchestrator";
import { trackTourAnalytics } from "@/components/tour/tour-analytics";
import { TourQueryListener } from "@/components/tour/TourQueryListener";
import { TourStepModal } from "@/components/tour/TourStepModal";
import { TourStepsWidget } from "@/components/tour/TourStepsWidget";
import type { TourSideEffect } from "@/components/tour/engine/types";
import { onboardingTourEvents } from "@/tours/onboarding/events";
import { toursEnabled } from "@/lib/tours-config";
import { useTourStore } from "@/stores/tour.store";
import { getActiveTour, type TourId } from "@/tours/registry";
import type { AnyTourEvents } from "@/tours/types";
import { getTourRouteParams } from "@/tours/utils/getTourRouteParams";

type Props = {
  emitter: Emitter<AnyTourEvents>;
  children: React.ReactNode;
};

export function TourProvider({ emitter, children }: Props) {
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
  const setRouteParams = useTourStore((state) => state.actions.setRouteParams);
  const minimizeGuidance = useTourStore((state) => state.actions.minimizeGuidance);
  const routeParams = useTourStore((state) => state.routeParams);
  const guidanceVisible = useTourStore((state) => state.guidanceVisible);

  const locationRef = useRef(location.pathname);
  locationRef.current = location.pathname;

  const getRouteParamsForTour = useCallback(() => {
    return getTourRouteParams(useTourStore.getState().routeParams, locationRef.current);
  }, []);

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
        onMinimizeGuidance: () => minimizeGuidance(),
        onStatusChange: () => {},
        onAnalytics: trackTourAnalytics,
        onTourSideEffect: (effect: TourSideEffect) => {
          if (effect.type === "open-first-trace") {
            onboardingTourEvents.emit("onboarding:request-open-first-trace", undefined);
          }
        },
      },
      getRouteParamsForTour,
      () => useTourStore.getState().guidanceVisible
    );

    return orchestratorRef.current;
  }, [completeTour, dismissTour, emitter, getRouteParamsForTour, minimizeGuidance, setStep, stopTour]);

  useEffect(() => {
    const effectiveParams = getTourRouteParams(routeParams, location.pathname);
    const hasChanges =
      (effectiveParams.taskId && routeParams.taskId !== effectiveParams.taskId) ||
      (effectiveParams.datasetId && routeParams.datasetId !== effectiveParams.datasetId) ||
      (effectiveParams.promptName && routeParams.promptName !== effectiveParams.promptName);

    if (hasChanges) {
      setRouteParams(effectiveParams);
    }
  }, [location.pathname, routeParams.datasetId, routeParams.promptName, routeParams.taskId, setRouteParams]);

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
      if (result.action === "navigate" && !result.route.includes(":")) {
        navigate(result.route, { replace: true });
      }
    });
  }, [activeStepId, activeTourId, guidanceVisible, initOrchestrator, location.pathname, navigate, routeParams, stopTour]);

  return (
    <TourEmitterContext.Provider value={emitter}>
      {toursEnabled && <TourQueryListener />}
      {toursEnabled && <TourStepModal />}
      {toursEnabled && <TourStepsWidget />}
      {children}
    </TourEmitterContext.Provider>
  );
}
