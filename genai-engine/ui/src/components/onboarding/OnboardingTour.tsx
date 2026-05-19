import { alpha, useTheme } from "@mui/material/styles";
import { useEffect, useMemo, useRef } from "react";
import Joyride, { ACTIONS, EVENTS, STATUS, type CallBackProps, type Step } from "react-joyride";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { runStepAction, useStepAction } from "./hooks/useStepAction";
import { useWaitForTarget } from "./hooks/useWaitForTarget";
import { OnboardingTooltip } from "./OnboardingTooltip";
import { tourRoutes } from "./routes";
import { resolveStepTarget, STEP_IDS, STEPS, type TourStep } from "./steps";
import { useOnboardingStore } from "./stores/onboarding.store";

const pathFromHref = (href: string): string => href.split("?")[0];

const matchesArrival = (pathname: string, step: TourStep, taskId: string): boolean => {
  if (!step.route?.advanceOnArrival) return false;
  return pathname.endsWith(pathFromHref(step.route.href(taskId)));
};

const joyrideSteps: Step[] = STEPS.map((s) => ({
  target: resolveStepTarget(s.target),
  title: s.title,
  content: s.body,
  placement: s.placement,
  disableBeacon: true,
  spotlightClicks: s.spotlightClicks,
  ...(s.overlayClickThrough && {
    styles: { overlay: { pointerEvents: "none" as const } },
  }),
}));

export const OnboardingTour = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { id: taskId } = useParams<{ id: string }>();

  const status = useOnboardingStore((s) => s.status);
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const next = useOnboardingStore((s) => s.next);
  const dismiss = useOnboardingStore((s) => s.dismiss);

  const step = STEPS[currentStep];
  const stepEntryPathRef = useRef<string | null>(null);

  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const taskIdRef = useRef(taskId);
  taskIdRef.current = taskId;
  const locationPathnameRef = useRef(location.pathname);
  locationPathnameRef.current = location.pathname;

  useStepAction(STEP_IDS.VIEW_TRACES, () => {
    if (taskId) navigate(tourRoutes.traces(taskId));
  });
  useStepAction(STEP_IDS.VIEW_DATASETS, () => {
    if (taskId) navigate(tourRoutes.datasets(taskId));
  });
  useStepAction(STEP_IDS.VIEW_PROMPTS, () => {
    if (taskId) navigate(tourRoutes.promptsManagement(taskId));
  });

  // Navigate when a step is entered
  useEffect(() => {
    const handleStepEnter = (stepIndex: number) => {
      const tid = taskIdRef.current;
      if (!tid) return;
      const s = STEPS[stepIndex];
      if (!s) return;
      stepEntryPathRef.current = locationPathnameRef.current;
      if (!s.route || s.route.advanceOnArrival) return;
      const target = s.route.href(tid);
      if (window.location.pathname + window.location.search === target) return;
      navigateRef.current(target);
    };

    const initial = useOnboardingStore.getState();
    if (initial.status === "active") handleStepEnter(initial.currentStep);

    return useOnboardingStore.subscribe(
      (s) => ({ status: s.status, currentStep: s.currentStep }),
      (curr, prev) => {
        if (curr.status !== "active") return;
        const becameActive = prev.status !== "active";
        const stepChanged = curr.currentStep !== prev.currentStep;
        if (!becameActive && !stepChanged) return;
        handleStepEnter(curr.currentStep);
      },
      { equalityFn: (a, b) => a.status === b.status && a.currentStep === b.currentStep }
    );
  }, []);

  // Advance on arrival
  useEffect(() => {
    if (status !== "active" || !step || !taskId) return;
    if (!matchesArrival(location.pathname, step, taskId)) return;
    if (stepEntryPathRef.current === location.pathname) return;
    next();
  }, [status, step?.id, location.pathname, taskId, next, step]);

  const targetSelector = step ? resolveStepTarget(step.target) : null;
  const targetReady = useWaitForTarget(targetSelector, [currentStep]);

  const joyrideStyles = useMemo(
    () => ({
      options: {
        zIndex: theme.zIndex.modal + 10,
        primaryColor: theme.palette.primary.main,
        backgroundColor: theme.palette.background.paper,
        textColor: theme.palette.text.primary,
        arrowColor: theme.palette.background.paper,
        overlayColor: alpha(theme.palette.common.black, 0.55),
      },
      spotlight: {
        borderRadius: 8,
      },
    }),
    [theme]
  );

  const handleCallback = (data: CallBackProps) => {
    const { action, type, status: joyrideStatus, index: callbackIndex } = data;

    if (joyrideStatus === STATUS.SKIPPED || action === ACTIONS.CLOSE) {
      dismiss();
      return;
    }

    if (joyrideStatus === STATUS.FINISHED) {
      return;
    }

    if (type === EVENTS.STEP_AFTER && action === ACTIONS.NEXT) {
      // Joyride re-fires STEP_AFTER+NEXT whenever stepIndex changes externally
      const liveCurrentStep = useOnboardingStore.getState().currentStep;
      if (callbackIndex < liveCurrentStep) return;

      const stepConfig = STEPS[liveCurrentStep];
      if (!stepConfig) return;

      runStepAction(stepConfig.id);
      const afterStep = useOnboardingStore.getState().currentStep;
      if (afterStep === liveCurrentStep) next();
    }
  };

  const run = status === "active" && targetReady;

  return (
    <Joyride
      steps={joyrideSteps}
      stepIndex={currentStep}
      run={run}
      continuous
      showProgress={false}
      showSkipButton
      disableOverlayClose
      hideCloseButton
      disableScrolling
      disableScrollParentFix
      spotlightPadding={6}
      callback={handleCallback}
      tooltipComponent={OnboardingTooltip}
      styles={joyrideStyles}
      floaterProps={{
        disableAnimation: false,
        disableFlip: true,
        options: {
          preventOverflow: {
            boundariesElement: "viewport",
            padding: 32,
          },
        },
      }}
    />
  );
};
