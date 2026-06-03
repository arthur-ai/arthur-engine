import type { WildcardHandler } from "mitt";

import type { TourEvents, TourPlugin } from "../core/types";

export interface CreateAnalyticsPluginOptions {
  track: (name: string, props?: Record<string, unknown>) => void;
  prefix?: string;
  /**
   * Optional event-name filter. Defaults to forwarding every bus event. Pass
   * a list to keep analytics noise down (`step:left` is high-volume since it
   * fires on prev/dismiss too).
   */
  include?: ReadonlyArray<keyof TourEvents>;
}

/**
 * Forwards engine bus events to a caller-supplied tracker. v1 surface
 * upgrade: `step:completed` (forward-progress only) replaces v0's
 * `step:advance` (which also fired on `prev`/`goTo`).
 *
 * The wildcard subscription is also the central place to measure per-step
 * dwell time: it stamps each `step:enter` and appends `duration_seconds`
 * (elapsed since that enter) to the matching `step:completed` / `step:left`.
 */
export function createAnalyticsPlugin(opts: CreateAnalyticsPluginOptions): TourPlugin {
  const prefix = opts.prefix ?? "tour";
  const include = opts.include ? new Set<keyof TourEvents>(opts.include) : null;

  return {
    name: "analytics",
    install: ({ bus }) => {
      // Per-step enter timestamps (monotonic ms). Keyed by section:step so a
      // re-entered step (prev → forward) is timed from its latest `step:enter`.
      const enteredAt = new Map<string, number>();
      const stepKey = (props: Record<string, unknown>) => `${props.sectionId}:${props.stepId}`;

      const handler: WildcardHandler<TourEvents> = (type, event) => {
        const props = event as Record<string, unknown>;

        // Stamp regardless of the `include` filter so duration survives even
        // when `step:enter` itself is filtered out of forwarding.
        if (type === "step:enter") {
          enteredAt.set(stepKey(props), performance.now());
        }

        if (include && !include.has(type as keyof TourEvents)) return;

        // A forward exit fires both `step:completed` and `step:left` (completed
        // ⊂ left); enrich both, then drop the timestamp only on the terminal
        // `step:left` so it stays available to the preceding `step:completed`
        // and the map stays bounded. A missing stamp (e.g. `auto-skip`, which
        // never emits `step:enter`) simply forwards without a duration.
        if (type === "step:completed" || type === "step:left") {
          const startedAt = enteredAt.get(stepKey(props));
          if (startedAt !== undefined) {
            if (type === "step:left") enteredAt.delete(stepKey(props));
            opts.track(`${prefix}.${String(type)}`, { ...props, duration_seconds: Math.round((performance.now() - startedAt) / 100) / 10 });
            return;
          }
        }

        opts.track(`${prefix}.${String(type)}`, props);
      };
      bus.on("*", handler);
      return () => bus.off("*", handler);
    },
  };
}
