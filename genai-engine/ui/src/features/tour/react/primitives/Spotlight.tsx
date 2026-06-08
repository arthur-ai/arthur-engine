import { useEffect, useState, type CSSProperties } from "react";

import type { HighlightSpec } from "../../core/types";
import { useTourEngine } from "../useTour";

/** Track `prefers-reduced-motion` so the spotlight pulse can be suppressed. */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return reduced;
}

export interface SpotlightProps {
  rect: DOMRect | null;
  highlight?: HighlightSpec;
  backdropColor?: string;
  className?: string;
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
      return { shape: "box", padding: spec.padding ?? 8, radius: spec.radius ?? 8, pulse: spec.pulse ?? false };
    case "circle":
      return { shape: "circle", padding: spec.padding ?? 8, radius: 0, pulse: spec.pulse ?? false };
    case "none":
      return { ...fallback, shape: "none" };
    case "custom":
    default:
      return fallback;
  }
}

/**
 * Fixed full-screen SVG with a cutout around `rect`. Custom highlights
 * delegate to the renderer registered via `registerHighlight(key, renderer)`;
 * unregistered keys fall back to the default box cutout.
 */
export function Spotlight({ rect, highlight, backdropColor = "rgba(0, 0, 0, 0.55)", className, style }: SpotlightProps) {
  const engine = useTourEngine();
  const reducedMotion = usePrefersReducedMotion();

  if (highlight?.shape === "custom") {
    const renderer = engine.getHighlight(highlight.key);
    if (renderer) {
      return <>{renderer({ rect, spec: highlight, backdropColor, style })}</>;
    }
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
      {norm.pulse && !reducedMotion ? (
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
