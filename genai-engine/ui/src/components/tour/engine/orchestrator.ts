import { driver, type Driver } from "driver.js";
import type { Emitter } from "mitt";

import { waitForElement } from "@/components/tour/utils/waitForElement";
import type { FlatTourStep } from "@/tours/registry";
import { getFlatSteps } from "@/tours/registry";
import type { AnyTourEvents, Tour, TourStep } from "@/tours/types";
import { isStepOnCurrentRoute } from "@/tours/utils";
import { resolveStepRoute } from "@/tours/utils/resolveStepRoute";

import { mapTourStepsToDriver } from "./mapStepToDriver";
import type { OrchestratorTickResult, TourAnalyticsPayload, TourOrchestratorCallbacks, TourRuntimeStatus } from "./types";

export class TourOrchestrator<Events extends AnyTourEvents = AnyTourEvents> {
  private driver: Driver | null = null;
  private tour: Tour<Events> | null = null;
  private flatSteps: FlatTourStep<Events>[] = [];
  private currentStepIndex = 0;
  private status: TourRuntimeStatus = { status: "idle" };
  private eventUnsubscribe: (() => void) | null = null;
  private tickGeneration = 0;
  private destroyingDriver = false;

  constructor(
    private readonly emitter: Emitter<Events>,
    private readonly callbacks: TourOrchestratorCallbacks,
    private readonly getRouteParams: () => Record<string, string>
  ) {}

  getStatus(): TourRuntimeStatus {
    return this.status;
  }

  getCurrentStep(): FlatTourStep<Events> | null {
    return this.flatSteps[this.currentStepIndex] ?? null;
  }

  start(tour: Tour<Events>, stepId?: string): void {
    this.destroyDriver();
    this.clearEventSubscription();
    this.tour = tour;
    this.flatSteps = getFlatSteps(tour);

    const index = stepId ? this.flatSteps.findIndex((step) => step.id === stepId) : 0;
    if (index < 0 || this.flatSteps.length === 0) {
      return;
    }

    this.currentStepIndex = index;
    this.initDriver();

    const step = this.flatSteps[this.currentStepIndex];
    this.callbacks.onStepChange(step.id);
    this.emitAnalytics({
      type: "started",
      tourId: tour.id,
      stepId: step.id,
      sectionId: step.sectionId,
    });
  }

  async tick(pathname: string): Promise<OrchestratorTickResult> {
    if (!this.tour || this.flatSteps.length === 0) {
      return { action: "none" };
    }

    const generation = ++this.tickGeneration;
    const step = this.flatSteps[this.currentStepIndex];
    const routeParams = { ...this.getRouteParams(), ...step.routeParams };
    const resolvedRoute = resolveStepRoute(step.route, routeParams);

    if (!isStepOnCurrentRoute(step, pathname, routeParams)) {
      this.setStatus({ status: "navigating", stepId: step.id, route: resolvedRoute });
      return { action: "navigate", route: resolvedRoute };
    }

    this.setStatus({ status: "waitingTarget", stepId: step.id });

    try {
      await waitForElement(step.selector);
    } catch (error) {
      if (generation !== this.tickGeneration) {
        return { action: "none" };
      }

      const reason = error instanceof Error ? error.message : "Tour target not found";
      this.setStatus({ status: "error", stepId: step.id, reason });
      this.emitAnalytics({
        type: "error",
        tourId: this.tour.id,
        stepId: step.id,
        sectionId: step.sectionId,
        errorReason: reason,
      });
      return { action: "error", reason };
    }

    if (generation !== this.tickGeneration) {
      return { action: "none" };
    }

    if (!this.driver) {
      this.initDriver();
    }

    this.driver?.drive(this.currentStepIndex);
    this.setStatus({ status: "showing", stepId: step.id, stepIndex: this.currentStepIndex });
    this.emitAnalytics({
      type: "step_viewed",
      tourId: this.tour.id,
      stepId: step.id,
      sectionId: step.sectionId,
    });

    if (step.type === "task") {
      this.subscribeToTaskEvent(step);
    } else {
      this.clearEventSubscription();
    }

    return { action: "none" };
  }

  next(): void {
    const step = this.flatSteps[this.currentStepIndex];
    if (!step || !this.tour) {
      return;
    }

    this.emitAnalytics({
      type: "step_completed",
      tourId: this.tour.id,
      stepId: step.id,
      sectionId: step.sectionId,
    });

    if (this.currentStepIndex >= this.flatSteps.length - 1) {
      this.complete();
      return;
    }

    this.clearEventSubscription();
    this.currentStepIndex += 1;
    const nextStep = this.flatSteps[this.currentStepIndex];
    this.callbacks.onStepChange(nextStep.id);
  }

  prev(): void {
    if (this.currentStepIndex <= 0) {
      return;
    }

    this.clearEventSubscription();
    this.currentStepIndex -= 1;
    const prevStep = this.flatSteps[this.currentStepIndex];
    this.callbacks.onStepChange(prevStep.id);
  }

  goTo(stepId: string): void {
    const index = this.flatSteps.findIndex((step) => step.id === stepId);
    if (index < 0) {
      return;
    }

    this.clearEventSubscription();
    this.currentStepIndex = index;
    this.callbacks.onStepChange(this.flatSteps[index].id);
  }

  skipStep(): void {
    const step = this.flatSteps[this.currentStepIndex];
    if (!step || !this.tour) {
      return;
    }

    this.emitAnalytics({
      type: "skipped",
      tourId: this.tour.id,
      stepId: step.id,
      sectionId: step.sectionId,
      reason: "user_skip",
    });
    this.next();
  }

  retryStep(): void {
    const step = this.flatSteps[this.currentStepIndex];
    if (!step) {
      return;
    }

    this.setStatus({ status: "waitingTarget", stepId: step.id });
  }

  stop(): void {
    this.destroyDriver();
    this.clearEventSubscription();
    this.tour = null;
    this.flatSteps = [];
    this.currentStepIndex = 0;
    this.setStatus({ status: "idle" });
    this.callbacks.onTourStop();
  }

  destroy(): void {
    this.stop();
  }

  private complete(): void {
    if (!this.tour) {
      return;
    }

    const tourId = this.tour.id;
    this.emitAnalytics({ type: "completed", tourId });
    this.setStatus({ status: "completed", tourId });
    this.destroyDriver();
    this.clearEventSubscription();
    this.tour = null;
    this.flatSteps = [];
    this.callbacks.onTourComplete(tourId);
  }

  private initDriver(): void {
    this.destroyDriver();

    this.driver = driver({
      allowClose: true,
      showProgress: true,
      progressText: "{{current}} of {{total}}",
      popoverClass: "arthur-tour-popover",
      steps: mapTourStepsToDriver(this.flatSteps),
      onNextClick: () => {
        const step = this.flatSteps[this.currentStepIndex];
        if (step?.type === "task") {
          return;
        }
        this.next();
      },
      onPrevClick: () => {
        this.prev();
      },
      onCloseClick: () => {
        this.handleDismiss();
      },
      onDestroyed: () => {
        if (this.destroyingDriver || !this.tour) {
          return;
        }
        this.handleDismiss();
      },
    });
  }

  private handleDismiss(): void {
    const step = this.flatSteps[this.currentStepIndex];
    const tourId = this.tour?.id;

    if (step && tourId) {
      this.emitAnalytics({
        type: "skipped",
        tourId,
        stepId: step.id,
        sectionId: step.sectionId,
        reason: "user_closed",
      });
    }

    this.destroyDriver();
    this.clearEventSubscription();
    this.tour = null;
    this.flatSteps = [];
    this.currentStepIndex = 0;
    this.setStatus({ status: "idle" });

    if (tourId) {
      this.callbacks.onTourDismiss(tourId);
    }
  }

  private subscribeToTaskEvent(step: TourStep<Events> & { type: "task" }): void {
    this.clearEventSubscription();
    this.setStatus({ status: "waitingEvent", stepId: step.id, eventName: step.waitFor });

    const handler = () => {
      this.clearEventSubscription();
      this.next();
    };

    this.emitter.on(step.waitFor, handler);
    this.eventUnsubscribe = () => {
      this.emitter.off(step.waitFor, handler);
    };
  }

  private clearEventSubscription(): void {
    this.eventUnsubscribe?.();
    this.eventUnsubscribe = null;
  }

  private destroyDriver(): void {
    if (this.driver?.isActive()) {
      this.destroyingDriver = true;
      this.driver.destroy();
      this.destroyingDriver = false;
    }
    this.driver = null;
  }

  private setStatus(status: TourRuntimeStatus): void {
    this.status = status;
    this.callbacks.onStatusChange(status);
  }

  private emitAnalytics(payload: TourAnalyticsPayload): void {
    this.callbacks.onAnalytics(payload);
  }
}
