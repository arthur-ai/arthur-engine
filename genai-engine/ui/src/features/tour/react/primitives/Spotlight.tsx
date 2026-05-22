import type { CSSProperties } from "react";

import type { HighlightSpec } from "../../core/types";
import { useTourEngine } from "../useTour";

export interface SpotlightProps {
  rect: DOMRect | null;
  highlight?: HighlightSpec;
  /** Backdrop color (rgba). Defaults to a translucent black. */
  backdropColor?: string;
  /** Optional additional className for the SVG. */
  className?: string;
  /** Inline style escape hatch (z-index, transitions, etc.). */
  style?: CSSProperties;
}

const MASK_ID = "tour-spotlight-mask";
const PULSE_KEYFRAMES = "tour-spotlight-pulse";

interface NormalizedHighlight {
  shape: "box" | "circle" | "none";
  padding: number;
  radius: number;
  pulse: boolean;
}

function normalize(spec: HighlightSpec | undefined): NormalizedHighlight {
  const fallback: NormalizedHighlight = { shape: "box", padding: 8, radius: 8, pulse: false };
  if (!spec) return fallback;
  switch (spec.shape) {
    case "box":
      return {
        shape: "box",
        padding: spec.padding ?? 8,
        radius: spec.radius ?? 8,
        pulse: spec.pulse ?? false,
      };
    case "circle":
      return {
        shape: "circle",
        padding: spec.padding ?? 8,
        radius: 0,
        pulse: spec.pulse ?? false,
      };
    case "none":
      return { ...fallback, shape: "none" };
    case "custom":
    default:
      // Custom shapes are rendered by plugins via the highlight registry; the
      // built-in Spotlight falls back to box.
      return fallback;
  }
}

/**
 * Fixed full-screen SVG with a cutout around `rect`. If the highlight is `none`
 * or the rect is missing, renders a flat backdrop. Pointer events are disabled
 * on the SVG so clicks fall through; consumers wrap this in a clickable div if
 * they want backdrop dismissal.
 *
 * For `highlight.shape === "custom"`, the rendering is delegated to the
 * plugin-registered renderer looked up via `engine.getHighlight(key)`. If no
 * renderer is registered for the key, the spotlight falls back to its default
 * box cutout — this primitive must therefore be mounted inside a
 * `<TourProvider>`, which all real usages already are.
 */
export function Spotlight({ rect, highlight, backdropColor = "rgba(0, 0, 0, 0.55)", className, style }: SpotlightProps) {
  const engine = useTourEngine();

  if (highlight?.shape === "custom") {
    const renderer = engine.getHighlight(highlight.key);
    if (renderer) {
      return <>{renderer({ rect, spec: highlight, backdropColor, style })}</>;
    }
    // No renderer registered for `highlight.key` — fall through to the
    // default box cutout below so the page is still dimmed for the user.
  }

  const norm = normalize(highlight);

  const baseStyle: CSSProperties = {
    position: "fixed",
    inset: 0,
    width: "100vw",
    height: "100vh",
    pointerEvents: "none",
    ...style,
  };

  if (norm.shape === "none" || !rect) {
    return (
      <svg aria-hidden="true" className={className} style={baseStyle}>
        <rect x={0} y={0} width="100%" height="100%" fill={backdropColor} />
      </svg>
    );
  }

  const x = rect.x - norm.padding;
  const y = rect.y - norm.padding;
  const width = rect.width + norm.padding * 2;
  const height = rect.height + norm.padding * 2;
  const cx = rect.x + rect.width / 2;
  const cy = rect.y + rect.height / 2;
  const radius = Math.max(width, height) / 2;

  return (
    <svg aria-hidden="true" className={className} style={baseStyle}>
      <defs>
        <mask id={MASK_ID}>
          <rect x={0} y={0} width="100%" height="100%" fill="white" />
          {norm.shape === "box" ? (
            <rect x={x} y={y} width={width} height={height} rx={norm.radius} fill="black" />
          ) : (
            <circle cx={cx} cy={cy} r={radius} fill="black" />
          )}
        </mask>
      </defs>
      <rect x={0} y={0} width="100%" height="100%" fill={backdropColor} mask={`url(#${MASK_ID})`} />
      {norm.pulse ? (
        <>
          <style>{`@keyframes ${PULSE_KEYFRAMES} { 0% { opacity: 0.85; } 100% { opacity: 0; } }`}</style>
          {norm.shape === "box" ? (
            <rect
              x={x - 2}
              y={y - 2}
              width={width + 4}
              height={height + 4}
              rx={norm.radius + 2}
              fill="none"
              stroke="white"
              strokeWidth={2}
              style={{ animation: `${PULSE_KEYFRAMES} 1.6s ease-out infinite` }}
            />
          ) : (
            <circle
              cx={cx}
              cy={cy}
              r={radius + 4}
              fill="none"
              stroke="white"
              strokeWidth={2}
              style={{ animation: `${PULSE_KEYFRAMES} 1.6s ease-out infinite` }}
            />
          )}
        </>
      ) : null}
    </svg>
  );
}
