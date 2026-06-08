import type { QueryHookResolver, TargetSpec } from "./types";

export interface FindElementByExactTextOptions {
  root?: ParentNode;
  selector?: string;
  closestSelector?: string;
}

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
      return pickSelectorMatch(spec.selector);
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
 * Resolve a CSS selector to a single Element. When the selector matches more
 * than one node — e.g. a stale node mid route-exit-animation alongside the live
 * one, both carrying the same `data-tour-id` — prefer the first match that is
 * connected and actually rendered. `document.querySelector` would return
 * whichever comes first in document order, which can be the stale twin and
 * strands the spotlight on it. Falls back to the first match when nothing is
 * rendered (or in layout-less environments like jsdom).
 */
function pickSelectorMatch(selector: string): Element | null {
  const matches = document.querySelectorAll(selector);
  if (matches.length <= 1) return matches[0] ?? null;
  for (const el of matches) {
    if (isRenderedElement(el)) return el;
  }
  return matches[0] ?? null;
}

/** True when the element is attached to the document and generates layout boxes. */
function isRenderedElement(el: Element): boolean {
  return el.isConnected && el.getClientRects().length > 0;
}

export function findElementByExactText(text: string, options: FindElementByExactTextOptions = {}): Element | null {
  const { root = document, selector = "*", closestSelector } = options;
  const expectedText = normalizeElementText(text);
  const candidates = Array.from(root.querySelectorAll(selector));
  const match = candidates.find((element) => normalizeElementText(element.textContent ?? "") === expectedText);
  if (!match) return null;
  return closestSelector ? (match.closest(closestSelector) ?? match) : match;
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

function normalizeElementText(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}
