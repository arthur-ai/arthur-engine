import { vi } from "vitest";

class TestIntersectionObserver implements IntersectionObserver {
  readonly root: Element | Document | null = null;
  readonly rootMargin = "";
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
