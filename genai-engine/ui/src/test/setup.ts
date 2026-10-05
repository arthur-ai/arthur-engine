import { afterAll, vi } from "vitest";

class TestIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin = "";
  readonly scrollMargin = "";
  readonly thresholds: ReadonlyArray<number> = [];

  disconnect(): void {}
  observe(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
  unobserve(): void {}
}

Object.defineProperty(window, "IntersectionObserver", {
  configurable: true,
  writable: true,
  value: TestIntersectionObserver,
});

Object.defineProperty(globalThis, "IntersectionObserver", {
  configurable: true,
  writable: true,
  value: TestIntersectionObserver,
});

if (!window.requestAnimationFrame) {
  window.requestAnimationFrame = (callback) => window.setTimeout(() => callback(performance.now()), 16);
}

if (!window.cancelAnimationFrame) {
  window.cancelAnimationFrame = (handle) => window.clearTimeout(handle);
}

vi.stubGlobal("requestAnimationFrame", window.requestAnimationFrame.bind(window));
vi.stubGlobal("cancelAnimationFrame", window.cancelAnimationFrame.bind(window));

// jsdom has no AnimationEvent; React only registers unprefixed animation events
// (onAnimationEnd et al.) when `AnimationEvent in window` at react-dom import time.
if (typeof window.AnimationEvent === "undefined") {
  class AnimationEventPolyfill extends Event {
    readonly animationName: string;
    readonly elapsedTime: number;
    readonly pseudoElement: string;

    constructor(type: string, init: AnimationEventInit = {}) {
      super(type, init);
      this.animationName = init.animationName ?? "";
      this.elapsedTime = init.elapsedTime ?? 0;
      this.pseudoElement = init.pseudoElement ?? "";
    }
  }
  window.AnimationEvent = AnimationEventPolyfill as unknown as typeof AnimationEvent;
  vi.stubGlobal("AnimationEvent", window.AnimationEvent);
}

// React routes commits and passive-effect flushes through its Scheduler, which uses
// setImmediate under Node. An update that lands outside act() (a late promise or timer)
// leaves that work queued, and if Vitest tears the jsdom environment down first the callback
// reads `window` after it is gone — an uncaught ReferenceError that fails the run even though
// every test passed. Drain the queue while the environment is still alive; each callback can
// schedule the next step (commit, then passive effects, then any follow-up update), so drain
// a handful of ticks instead of one.
afterAll(async () => {
  for (let i = 0; i < 10; i++) {
    await new Promise<void>((resolve) => {
      setImmediate(() => resolve());
    });
  }
});
