import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createTourEngine } from "../engine";
import type { TourConfig } from "../types";

// jsdom doesn't implement layout, so we stub the DOM methods the engine's
// occlusion check relies on (elementFromPoint, getClientRects,
// getBoundingClientRect) and neutralize the enter-time rAF so the check is
// driven deterministically through `recheckOcclusion()`.
type HitDoc = { elementFromPoint?: (x: number, y: number) => Element | null };
const hitDoc = document as unknown as HitDoc;
const originalFromPoint = hitDoc.elementFromPoint;

function inViewportRect(): DOMRect {
  return { x: 10, y: 10, left: 10, top: 10, width: 100, height: 100, right: 110, bottom: 110, toJSON: () => ({}) } as DOMRect;
}

function makeLaidOutElement(): HTMLElement {
  const el = document.createElement("button");
  document.body.appendChild(el);
  el.getBoundingClientRect = () => inViewportRect();
  el.getClientRects = () => [inViewportRect()] as unknown as DOMRectList;
  return el;
}

function oneStepConfig(target: HTMLElement): TourConfig {
  return { id: "occ", sections: [{ id: "main", steps: [{ id: "one", target: { kind: "element", resolve: () => target }, content: "one" }] }] };
}

describe("engine occlusion detection", () => {
  beforeEach(() => {
    vi.stubGlobal("requestAnimationFrame", () => 0);
    vi.stubGlobal("cancelAnimationFrame", () => {});
  });

  afterEach(() => {
    hitDoc.elementFromPoint = originalFromPoint;
    document.body.innerHTML = "";
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("emits target:occluded with an occluderId when the target is covered", async () => {
    const target = makeLaidOutElement();
    const occluder = document.createElement("div");
    occluder.setAttribute("data-tour-id", "blocking-modal");
    document.body.appendChild(occluder);
    hitDoc.elementFromPoint = () => occluder;

    const engine = createTourEngine({ config: oneStepConfig(target) });
    const occluded: Array<{ occluderId: string; stepId: string }> = [];
    engine.on("target:occluded", (e) => occluded.push(e));

    await engine.start();
    engine.recheckOcclusion();

    expect(occluded).toHaveLength(1);
    expect(occluded[0]).toMatchObject({ stepId: "one", occluderId: "data-tour-id=blocking-modal" });
  });

  it("dedupes repeated occluded checks and emits revealed once the target clears", async () => {
    const target = makeLaidOutElement();
    const occluder = document.createElement("div");
    document.body.appendChild(occluder);
    let covered = true;
    hitDoc.elementFromPoint = () => (covered ? occluder : target);

    const engine = createTourEngine({ config: oneStepConfig(target) });
    let occluded = 0;
    let revealed = 0;
    engine.on("target:occluded", () => (occluded += 1));
    engine.on("target:revealed", () => (revealed += 1));

    await engine.start();
    engine.recheckOcclusion(); // covered → occluded
    engine.recheckOcclusion(); // still covered → deduped (no second emit)
    expect(occluded).toBe(1);
    expect(revealed).toBe(0);

    covered = false;
    engine.recheckOcclusion(); // now visible → revealed
    engine.recheckOcclusion(); // still visible → deduped
    expect(revealed).toBe(1);
  });

  it("does not emit occlusion when the target is topmost", async () => {
    const target = makeLaidOutElement();
    hitDoc.elementFromPoint = () => target;

    const engine = createTourEngine({ config: oneStepConfig(target) });
    let occluded = 0;
    engine.on("target:occluded", () => (occluded += 1));

    await engine.start();
    engine.recheckOcclusion();

    expect(occluded).toBe(0);
  });
});
