import type { QueryHookResolver, TargetSpec } from "./types";

export interface ResolveTargetOptions {
  timeoutMs?: number;
  signal?: AbortSignal;
  /**
   * Lookup function for `queryHook` targets. The engine wires this to read
   * from the per-tour Zustand store's `queryHooks` slice.
   */
  resolveQueryHook?: (hookId: string) => QueryHookResolver | undefined;
}

/**
 * Synchronously resolve a target to an Element if it currently exists, or null.
 * For `queryHook` targets the resolver is invoked synchronously — it MUST be a
 * pure read (no async, no React rendering).
 */
export function resolveTargetSync(spec: TargetSpec, options: Pick<ResolveTargetOptions, "resolveQueryHook"> = {}): Element | null {
  switch (spec.kind) {
    case "selector":
      return document.querySelector(spec.selector);
    case "element":
      return spec.resolve();
    case "ref":
      return spec.ref.current ?? null;
    case "queryHook": {
      const resolver = options.resolveQueryHook?.(spec.hookId);
      return resolver ? resolver() : null;
    }
  }
}

/**
 * Asynchronously resolve a target. Selector/element/ref targets fall back to
 * mutation observers as in v0. `queryHook` targets poll the registered
 * resolver on `requestAnimationFrame` since the registry write isn't a DOM
 * event — the consumer registers from a React effect, and the next animation
 * frame catches the update reliably without depending on `MutationObserver`
 * firing for an unrelated change.
 */
export function resolveTargetAsync(spec: TargetSpec, options: ResolveTargetOptions = {}): Promise<Element | null> {
  const immediate = resolveTargetSync(spec, options);
  if (immediate) return Promise.resolve(immediate);

  const { timeoutMs = 0, signal } = options;
  if (timeoutMs <= 0) return Promise.resolve(null);

  return new Promise<Element | null>((resolve) => {
    let resolved = false;
    let observer: MutationObserver | null = null;
    let timeoutId: number | null = null;
    let abortHandler: (() => void) | null = null;
    let frameId: number | null = null;

    const cleanup = () => {
      if (observer) {
        observer.disconnect();
        observer = null;
      }
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
        timeoutId = null;
      }
      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
        frameId = null;
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
      const el = resolveTargetSync(spec, options);
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

    if (spec.kind === "queryHook") {
      const poll = () => {
        if (resolved) return;
        check();
        if (resolved) return;
        frameId = window.requestAnimationFrame(poll);
      };
      frameId = window.requestAnimationFrame(poll);
    } else {
      observer = new MutationObserver(check);
      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: spec.kind === "selector" ? attributeFilterFromSelector(spec.selector) : undefined,
      });
    }

    timeoutId = window.setTimeout(() => finish(null), timeoutMs);
  });
}

function attributeFilterFromSelector(selector: string): string[] | undefined {
  const match = selector.match(/\[([a-zA-Z0-9-]+)/);
  if (!match) return undefined;
  return [match[1]];
}
