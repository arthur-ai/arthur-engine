import type { WildcardHandler } from "mitt";

import type { TourEvents, TourPlugin } from "../core/types";

export interface CreateAnalyticsPluginOptions {
  /** Caller-provided tracker. Decouples the plugin from any specific analytics vendor. */
  track: (name: string, props?: Record<string, unknown>) => void;
  /** Event-name prefix. Defaults to `"tour"`, producing names like `tour.step:enter`. */
  prefix?: string;
}

/**
 * Forwards every tour bus event to the provided `track` function. The plugin
 * is intentionally decoupled from the app's analytics implementation — wire it
 * up at the call site (e.g. with `track` from `@/services/amplitude`).
 *
 * @example
 * ```ts
 * import { track } from "@/services/amplitude";
 * const tour = createTour({
 *   config: {...},
 *   plugins: [createAnalyticsPlugin({ track })],
 * });
 * ```
 */
export function createAnalyticsPlugin(opts: CreateAnalyticsPluginOptions): TourPlugin {
  const prefix = opts.prefix ?? "tour";

  return {
    name: "analytics",
    install: ({ bus }) => {
      const handler: WildcardHandler<TourEvents> = (type, event) => {
        opts.track(`${prefix}.${String(type)}`, event as Record<string, unknown>);
      };
      bus.on("*", handler);
      return () => bus.off("*", handler);
    },
  };
}
