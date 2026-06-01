import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface TourPortalProps {
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
 * Lightweight portal mounting tour overlays at `document.body`. Shares a
 * singleton host element so every overlay sits in the same stacking
 * context, avoiding clipping by ancestor `overflow: hidden`.
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
