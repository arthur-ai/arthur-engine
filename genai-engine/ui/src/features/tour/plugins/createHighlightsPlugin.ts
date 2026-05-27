import type { HighlightRenderer, TourPlugin } from "../core/types";

export interface HighlightsPluginEntry {
  key: string;
  renderer: HighlightRenderer;
}

export interface CreateHighlightsPluginOptions {
  highlights: HighlightsPluginEntry[];
}

/**
 * Plugin convenience: register a batch of highlight renderers on the engine
 * via the plugin contract. Equivalent to calling `registerHighlight` in a
 * one-off plugin's install hook, but lets consumers express the batch
 * declaratively at `createTour` time.
 */
export function createHighlightsPlugin(opts: CreateHighlightsPluginOptions): TourPlugin {
  return {
    name: "highlights",
    install: ({ registerHighlight }) => {
      for (const entry of opts.highlights) registerHighlight(entry.key, entry.renderer);
    },
  };
}
