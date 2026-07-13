import { PulsingRing, Spotlight, type HighlightRenderer, type TourPlugin } from "@arthur/shared-components/tour";

/**
 * Registry key for the task-tour brand highlight. Points at a renderer that
 * paints the standard box-shaped spotlight cutout PLUS an outward-pulsing
 * brand-coloured ring around the cutout.
 *
 * Steps reference this via `highlight: { shape: "custom", key:
 * TASK_TOUR_PULSE_HIGHLIGHT, padding, options }`. The renderer is registered
 * by {@link createTaskTourHighlightsPlugin} and looked up by the engine
 * (`engine.getHighlight`) when the React `Spotlight` primitive sees the
 * custom shape.
 */
export const TASK_TOUR_PULSE_HIGHLIGHT = "task-tour-pulse";

/**
 * Renderer-specific options carried through `HighlightSpec.options`.
 * `radius` controls the box cutout's corner rounding; `pulseRadius` is the
 * outer ring's corner radius (typically a touch larger than the cutout's so
 * the ring sits cleanly outside it).
 */
export interface TaskTourPulseOptions {
  radius?: number;
  pulseRadius?: number;
}

const renderTaskTourPulse: HighlightRenderer = ({ rect, spec, backdropColor, style }) => {
  // Defer to the panel-only treatment when no rect is resolved — matches the
  // surrounding `ChecklistTour` policy that suppresses the spotlight when the
  // target hasn't appeared yet.
  if (!rect) return null;
  const options = (spec.options ?? {}) as TaskTourPulseOptions;
  const padding = spec.padding ?? 6;
  const radius = options.radius ?? 10;
  const pulseRadius = options.pulseRadius ?? radius + 2;
  // The pulse must paint above the spotlight cutout but below any
  // BackdropBlocker the consumer layers on top, so it sits one tier above
  // the outer Spotlight's z-index. ChecklistTour reserves 1400 for the
  // pulse and 1401 for the blocker; this keeps that ordering implicit.
  const baseZ = typeof style?.zIndex === "number" ? style.zIndex : 1399;
  return (
    <>
      {/* Box cutout via the built-in `Spotlight` primitive — passing
          `shape: "box"` (not "custom") avoids re-entering the registry
          dispatch we're inside of. */}
      <Spotlight rect={rect} highlight={{ shape: "box", padding, radius, pulse: false }} backdropColor={backdropColor} style={style} />
      <PulsingRing rect={rect} padding={padding} radius={pulseRadius} zIndex={baseZ + 1} />
    </>
  );
};

/**
 * Plugin that registers task-tour-specific highlight renderers on the engine.
 * Currently exposes only {@link TASK_TOUR_PULSE_HIGHLIGHT}, but lives as a
 * plugin (rather than a one-off `engine.registerHighlight` call) so the
 * registration is expressed through the engine's plugin contract — same as
 * persistence, analytics, and progress.
 */
export function createTaskTourHighlightsPlugin(): TourPlugin {
  return {
    name: "task-tour-highlights",
    install: ({ registerHighlight }) => {
      registerHighlight(TASK_TOUR_PULSE_HIGHLIGHT, renderTaskTourPulse);
    },
  };
}
