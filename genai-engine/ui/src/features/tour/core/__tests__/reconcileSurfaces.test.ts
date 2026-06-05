import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createTourEngine } from "../engine";
import type { TourConfig, TourNavigator } from "../types";

const elementTarget = () => ({ kind: "element" as const, resolve: () => document.body });

function step(id: string, overrides: Partial<TourConfig["sections"][number]["steps"][number]> = {}) {
  return { id, target: elementTarget(), content: id, ...overrides };
}

function singleSection(steps: TourConfig["sections"][number]["steps"]): TourConfig {
  return { id: "tour", sections: [{ id: "main", steps }] };
}

describe("reconcileSurfaces (occluder reconcile-on-enter)", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("closes a registered occluder the entering step does not declare open", async () => {
    const close = vi.fn();
    let open = true;
    const engine = createTourEngine({ config: singleSection([step("one")]) });
    engine.store.getState().registerOccluder({
      id: "drawer",
      isOpen: () => open,
      close: () => {
        open = false;
        close();
      },
    });

    await engine.start();

    expect(close).toHaveBeenCalledTimes(1);
    expect(open).toBe(false);
  });

  it("default (no surfaces declared) closes every registered occluder", async () => {
    const closeA = vi.fn();
    const closeB = vi.fn();
    const engine = createTourEngine({ config: singleSection([step("one")]) });
    engine.store.getState().registerOccluder({ id: "a", isOpen: () => true, close: closeA });
    engine.store.getState().registerOccluder({ id: "b", isOpen: () => true, close: closeB });

    await engine.start();

    expect(closeA).toHaveBeenCalledTimes(1);
    expect(closeB).toHaveBeenCalledTimes(1);
  });

  it("keeps a declared-open occluder open without closing or re-opening it", async () => {
    const close = vi.fn();
    const open = vi.fn();
    const engine = createTourEngine({
      config: singleSection([step("one", { surfaces: { open: [{ id: "drawer" }] } })]),
    });
    engine.store.getState().registerOccluder({ id: "drawer", isOpen: () => true, close, open });

    await engine.start();

    // Already open + declared open → pure no-op: input inside it is preserved.
    expect(close).not.toHaveBeenCalled();
    expect(open).not.toHaveBeenCalled();
  });

  it("opens a declared-open occluder that is currently closed", async () => {
    let open = false;
    const onOpen = vi.fn(() => {
      open = true;
    });
    const engine = createTourEngine({
      config: singleSection([step("one", { surfaces: { open: [{ id: "drawer" }] } })]),
    });
    engine.store.getState().registerOccluder({ id: "drawer", isOpen: () => open, close: () => {}, open: onOpen });

    await engine.start();

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(open).toBe(true);
  });

  it("passes the declared open args through to open()", async () => {
    const onOpen = vi.fn();
    const engine = createTourEngine({
      config: singleSection([step("one", { surfaces: { open: [{ id: "drawer", args: { mode: "review" } }] } })]),
    });
    engine.store.getState().registerOccluder({ id: "drawer", isOpen: () => false, close: () => {}, open: onOpen });

    await engine.start();

    expect(onOpen).toHaveBeenCalledWith({ mode: "review" });
  });

  it("leaves a `keep` occluder untouched (neither closed nor opened)", async () => {
    const close = vi.fn();
    const open = vi.fn();
    const engine = createTourEngine({
      config: singleSection([step("one", { surfaces: { keep: ["drawer"] } })]),
    });
    engine.store.getState().registerOccluder({ id: "drawer", isOpen: () => true, close, open });

    await engine.start();

    expect(close).not.toHaveBeenCalled();
    expect(open).not.toHaveBeenCalled();
  });

  it("ignores a declared-open id that has no registered occluder", async () => {
    const engine = createTourEngine({
      config: singleSection([step("one", { surfaces: { open: [{ id: "not-mounted" }] } })]),
    });

    // No occluder registered for the id — must not throw.
    await expect(engine.start()).resolves.toBeUndefined();
    expect(engine.getState()).toMatchObject({ status: "step", stepId: "one" });
  });

  it("makes final occluder state a pure function of the entering step (free-jump safe)", async () => {
    let open = false;
    const engine = createTourEngine({
      config: singleSection([step("needs-drawer", { surfaces: { open: [{ id: "drawer" }] } }), step("no-drawer")]),
    });
    engine.store.getState().registerOccluder({
      id: "drawer",
      isOpen: () => open,
      close: () => {
        open = false;
      },
      open: () => {
        open = true;
      },
    });

    await engine.start(); // enters needs-drawer → opens drawer
    expect(open).toBe(true);

    await engine.goTo({ sectionId: "main", stepId: "no-drawer" }); // closes drawer
    expect(open).toBe(false);

    await engine.goTo({ sectionId: "main", stepId: "needs-drawer" }); // re-opens drawer
    expect(open).toBe(true);
  });

  it("closes (PASS 1) before opening (PASS 2) on the same entry", async () => {
    const calls: string[] = [];
    let aOpen = true;
    let bOpen = false;
    const engine = createTourEngine({
      config: singleSection([step("one", { surfaces: { open: [{ id: "b" }] } })]),
    });
    engine.store.getState().registerOccluder({
      id: "a",
      isOpen: () => aOpen,
      close: () => {
        aOpen = false;
        calls.push("close-a");
      },
    });
    engine.store.getState().registerOccluder({
      id: "b",
      isOpen: () => bOpen,
      close: () => {
        bOpen = false;
      },
      open: () => {
        bOpen = true;
        calls.push("open-b");
      },
    });

    await engine.start();

    expect(calls).toEqual(["close-a", "open-b"]);
  });

  it("clears a URL-driven occluder's stale params on entry, fixing the same-route nav gap", async () => {
    let location = { pathname: "/x", search: "?id=abc", hash: "" };
    const navigate = vi.fn(async (to: string) => {
      const url = new URL(to, "http://h");
      location = { pathname: url.pathname, search: url.search, hash: url.hash };
    });
    const navigator: TourNavigator = { getLocation: () => location, navigate };
    const engine = createTourEngine({
      // Step is already on `/x` with a stale `?id=abc`. The route declares no
      // search, so the engine's route-match would normally SKIP navigation and
      // leave the stale param. Reconcile clears it first.
      config: singleSection([step("one", { route: "/x" })]),
      navigator,
    });
    engine.store.getState().registerOccluder({
      id: "drawer",
      isOpen: () => location.search.includes("id="),
      close: () => {
        location = { ...location, search: "" };
        return Promise.resolve();
      },
    });

    await engine.start();

    expect(location.search).toBe(""); // reconcile cleared it
    expect(navigate).not.toHaveBeenCalled(); // route already matched once cleared
  });

  it("awaits async closes, then skips the open pass when a newer transition aborts mid-reconcile", async () => {
    let releaseClose: () => void = () => {};
    const closePromise = new Promise<void>((resolve) => {
      releaseClose = resolve;
    });
    const openB = vi.fn();
    let aOpen = true;
    let bOpen = false;
    const engine = createTourEngine({
      config: singleSection([
        step("neutral", { surfaces: { keep: ["a", "b"] } }), // leaves A open so `slow` can close it
        step("slow", { surfaces: { open: [{ id: "b" }] } }), // closes A (slow), would then open B
        step("fast"), // closes everything
      ]),
    });
    engine.store.getState().registerOccluder({
      id: "a",
      isOpen: () => aOpen,
      close: () => {
        aOpen = false;
        return closePromise; // PASS 1 await hangs here
      },
    });
    engine.store.getState().registerOccluder({
      id: "b",
      isOpen: () => bOpen,
      close: () => {
        bOpen = false;
      },
      open: () => {
        bOpen = true;
        openB();
      },
    });

    await engine.start(); // enters neutral (section already entered; A stays open)
    const slowPromise = engine.goTo({ sectionId: "main", stepId: "slow" });
    // Once `slow` is the active step, its reconcile has already called A.close and
    // is suspended awaiting the close promise in PASS 1.
    await vi.waitFor(() => expect(engine.getState()).toMatchObject({ stepId: "slow" }));

    await engine.goTo({ sectionId: "main", stepId: "fast" }); // aborts slow's enterStep
    releaseClose(); // resolve A's slow close → slow resumes, sees aborted, returns
    await slowPromise;

    // slow's PASS 2 (open B) was skipped by the abort check; fast never opens B.
    expect(openB).not.toHaveBeenCalled();
    expect(engine.getState()).toMatchObject({ status: "step", stepId: "fast" });
  });
});
