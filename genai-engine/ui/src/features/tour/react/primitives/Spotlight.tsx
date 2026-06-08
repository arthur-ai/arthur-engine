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
 * Fixed full-screen overlay with a cutout around `rect` using CSS box-shadow.
 * Custom highlights delegate to the renderer registered via
 * `registerHighlight(key, renderer)`; unregistered keys fall back to the
 * default box cutout.
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

  if (norm.shape === "none" || !rect) {
    return (
      <div
        aria-hidden="true"
        className={className}
        style={{
          position: "fixed",
          inset: 0,
          background: backdropColor,
          pointerEvents: "none",
          ...style,
        }}
      />
    );
  }

  const padding = norm.padding;

  let cutoutStyle: CSSProperties;
  let pulseStyle: CSSProperties | null = null;

  if (norm.shape === "circle") {
    const diameter = Math.max(rect.width + padding * 2, rect.height + padding * 2);
    const top = rect.y + rect.height / 2 - diameter / 2;
    const left = rect.x + rect.width / 2 - diameter / 2;

    cutoutStyle = {
      position: "fixed",
      top,
      left,
      width: diameter,
      height: diameter,
      borderRadius: "50%",
      boxShadow: `0 0 0 9999px ${backdropColor}`,
      pointerEvents: "none",
      ...style,
    };

    if (norm.pulse && !reducedMotion) {
      pulseStyle = {
        position: "fixed",
        top: top - 2,
        left: left - 2,
        width: diameter + 4,
        height: diameter + 4,
        borderRadius: "50%",
        border: "2px solid white",
        pointerEvents: "none",
        animation: `${PULSE_KEYFRAMES} 1.6s ease-out infinite`,
        zIndex: style?.zIndex,
      };
    }
  } else {
    const x = rect.x - padding;
    const y = rect.y - padding;
    const w = rect.width + padding * 2;
    const h = rect.height + padding * 2;

    cutoutStyle = {
      position: "fixed",
      top: y,
      left: x,
      width: w,
      height: h,
      borderRadius: norm.radius,
      boxShadow: `0 0 0 9999px ${backdropColor}`,
      pointerEvents: "none",
      ...style,
    };

    if (norm.pulse && !reducedMotion) {
      pulseStyle = {
        position: "fixed",
        top: y - 2,
        left: x - 2,
        width: w + 4,
        height: h + 4,
        borderRadius: norm.radius + 2,
        border: "2px solid white",
        pointerEvents: "none",
        animation: `${PULSE_KEYFRAMES} 1.6s ease-out infinite`,
        zIndex: style?.zIndex,
      };
    }
  }

  return (
    <>
      {norm.pulse && !reducedMotion && (
        <style>{`@keyframes ${PULSE_KEYFRAMES} { 0% { opacity: 0; } 10% { opacity: 0.85; } 100% { opacity: 0; } }`}</style>
      )}
      <div aria-hidden="true" className={className} style={cutoutStyle} />
      {pulseStyle && <div aria-hidden="true" style={pulseStyle} />}
    </>
  );
}
