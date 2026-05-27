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
 */
export function createAnalyticsPlugin(opts: CreateAnalyticsPluginOptions): TourPlugin {
  const prefix = opts.prefix ?? "tour";
  const include = opts.include ? new Set<keyof TourEvents>(opts.include) : null;

  return {
    name: "analytics",
    install: ({ bus }) => {
      const handler: WildcardHandler<TourEvents> = (type, event) => {
        if (include && !include.has(type as keyof TourEvents)) return;
        opts.track(`${prefix}.${String(type)}`, event as Record<string, unknown>);
      };
      bus.on("*", handler);
      return () => bus.off("*", handler);
    },
  };
}
