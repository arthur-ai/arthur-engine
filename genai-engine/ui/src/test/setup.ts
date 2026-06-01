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
