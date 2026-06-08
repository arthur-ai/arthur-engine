import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDelayedFlag } from "./useChecklistController";

const DELAY = 200;

describe("useDelayedFlag", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("stays false while inactive", () => {
    const { result } = renderHook(() => useDelayedFlag(false, DELAY));
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(DELAY * 2));
    expect(result.current).toBe(false);
  });

  it("does NOT flip on a transient activation shorter than the delay (the UP-4505 flash)", () => {
    const { result, rerender } = renderHook(({ active }) => useDelayedFlag(active, DELAY), {
      initialProps: { active: false },
    });

    // Target lost for a single frame, then re-resolved before the window elapses.
    rerender({ active: true });
    act(() => vi.advanceTimersByTime(DELAY - 50));
    expect(result.current).toBe(false);
    rerender({ active: false });

    // Even after plenty of time, the cancelled timer must not surface the flag.
    act(() => vi.advanceTimersByTime(DELAY * 2));
    expect(result.current).toBe(false);
  });

  it("flips true once active stays continuously past the delay", () => {
    const { result, rerender } = renderHook(({ active }) => useDelayedFlag(active, DELAY), {
      initialProps: { active: false },
    });

    rerender({ active: true });
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(DELAY - 1));
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe(true);
  });

  it("clears immediately when active goes false (no delay on the shown→cleared edge)", () => {
    const { result, rerender } = renderHook(({ active }) => useDelayedFlag(active, DELAY), {
      initialProps: { active: true },
    });

    act(() => vi.advanceTimersByTime(DELAY));
    expect(result.current).toBe(true);

    rerender({ active: false });
    expect(result.current).toBe(false);
  });
});
