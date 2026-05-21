import type { TargetSpec } from "./types";

export interface ResolveTargetOptions {
  timeoutMs?: number;
  signal?: AbortSignal;
}

/**
 * Synchronously resolve a target to an Element if it currently exists, or null.
 * Used by triggers and trackers that need to read the live element.
 */
export function resolveTargetSync(spec: TargetSpec): Element | null {
  switch (spec.kind) {
    case "selector":
      return document.querySelector(spec.selector);
    case "element":
      return spec.resolve();
    case "ref":
      return spec.ref.current ?? null;
  }
}

/**
 * Asynchronously resolve a target. If the element is already in the DOM, returns
 * immediately; otherwise observes mutations on `document.body` until the element
 * appears or the timeout elapses.
 *
 * - For "element" / "ref" targets we poll on mutations and animation frames since
 *   we have no selector to query.
 * - Resolves with `null` on timeout (the engine surfaces this via target:lost).
 */
export function resolveTargetAsync(spec: TargetSpec, options: ResolveTargetOptions = {}): Promise<Element | null> {
  const immediate = resolveTargetSync(spec);
  if (immediate) return Promise.resolve(immediate);

  const { timeoutMs = 0, signal } = options;
  if (timeoutMs <= 0) return Promise.resolve(null);

  return new Promise<Element | null>((resolve) => {
    let resolved = false;
    let observer: MutationObserver | null = null;
    let timeoutId: number | null = null;
    let abortHandler: (() => void) | null = null;

    const cleanup = () => {
      if (observer) {
        observer.disconnect();
        observer = null;
      }
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
        timeoutId = null;
      }
      if (abortHandler && signal) {
        signal.removeEventListener("abort", abortHandler);
        abortHandler = null;
      }
    };

    const finish = (value: Element | null) => {
      if (resolved) return;
      resolved = true;
      cleanup();
      resolve(value);
    };

    const check = () => {
      const el = resolveTargetSync(spec);
      if (el) finish(el);
    };

    if (signal) {
      if (signal.aborted) {
        finish(null);
        return;
      }
      abortHandler = () => finish(null);
      signal.addEventListener("abort", abortHandler);
    }

    observer = new MutationObserver(check);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: spec.kind === "selector" ? attributeFilterFromSelector(spec.selector) : undefined,
    });

    timeoutId = window.setTimeout(() => finish(null), timeoutMs);
  });
}

/**
 * Heuristic: when the selector is attribute-based (e.g. [data-tour-id="x"]),
 * limit MutationObserver to the relevant attribute name to reduce noise.
 */
function attributeFilterFromSelector(selector: string): string[] | undefined {
  const match = selector.match(/\[([a-zA-Z0-9-]+)/);
  if (!match) return undefined;
  return [match[1]];
}
