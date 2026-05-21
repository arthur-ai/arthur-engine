import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface TourPortalProps {
  /** Override the host element. Defaults to a singleton div appended to body. */
  container?: HTMLElement | null;
  children: ReactNode;
}

const HOST_ID = "tour-portal-root";

function ensureHost(): HTMLElement {
  let host = document.getElementById(HOST_ID);
  if (!host) {
    host = document.createElement("div");
    host.id = HOST_ID;
    document.body.appendChild(host);
  }
  return host;
}

/**
 * Lightweight portal that mounts tour overlays at body. Stable host id so all
 * primitives share the same z-index/stacking context and avoid clipping by
 * `overflow: hidden` ancestors.
 */
export function TourPortal({ container, children }: TourPortalProps) {
  const [host, setHost] = useState<HTMLElement | null>(container ?? null);

  useEffect(() => {
    if (container) {
      setHost(container);
      return;
    }
    setHost(ensureHost());
  }, [container]);

  if (!host) return null;
  return createPortal(children, host);
}
