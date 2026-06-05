import { afterEach, describe, expect, it, vi } from "vitest";

import { describeOccluder, detectOcclusion } from "../occlusion";

function makeRect(x: number, y: number, w: number, h: number): DOMRect {
  return {
    x,
    y,
    left: x,
    top: y,
    width: w,
    height: h,
    right: x + w,
    bottom: y + h,
    toJSON: () => ({}),
  } as DOMRect;
}

// jsdom doesn't implement elementFromPoint / elementsFromPoint, so we assign
// stubs directly (vi.spyOn requires the method to already exist) and restore
// the originals after each test.
type HitTestDoc = {
  elementFromPoint?: (x: number, y: number) => Element | null;
  elementsFromPoint?: (x: number, y: number) => Element[];
};
const hitDoc = document as unknown as HitTestDoc;
const originalFromPoint = hitDoc.elementFromPoint;
const originalElementsFromPoint = hitDoc.elementsFromPoint;

function stubHitTest(fromPoint: ((x: number, y: number) => Element | null) | undefined, stack?: (x: number, y: number) => Element[]) {
  hitDoc.elementFromPoint = fromPoint;
  if (stack) hitDoc.elementsFromPoint = stack;
}

describe("detectOcclusion", () => {
  afterEach(() => {
    hitDoc.elementFromPoint = originalFromPoint;
    hitDoc.elementsFromPoint = originalElementsFromPoint;
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("returns indeterminate when hit-testing is unavailable (jsdom / SSR)", () => {
    stubHitTest(undefined);
    const target = document.createElement("div");
    document.body.appendChild(target);

    expect(detectOcclusion(target, makeRect(10, 10, 100, 100))).toMatchObject({ occluded: false, reason: "indeterminate" });
  });

  it("returns indeterminate when every sample point yields no element", () => {
    stubHitTest(() => null);
    const target = document.createElement("div");
    document.body.appendChild(target);

    expect(detectOcclusion(target, makeRect(10, 10, 100, 100)).reason).toBe("indeterminate");
  });

  it("returns ok when the target is the topmost element at every sample point", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    stubHitTest(() => target);

    expect(detectOcclusion(target, makeRect(10, 10, 100, 100))).toMatchObject({ occluded: false, reason: "ok", occluder: null });
  });

  it("treats a descendant hit as the target being visible", () => {
    const target = document.createElement("div");
    const child = document.createElement("span");
    target.appendChild(child);
    document.body.appendChild(target);
    stubHitTest(() => child);

    expect(detectOcclusion(target, makeRect(0, 0, 100, 100)).reason).toBe("ok");
  });

  it("flags covered and reports the occluder when something is on top", () => {
    const target = document.createElement("div");
    const occluder = document.createElement("div");
    occluder.setAttribute("data-tour-id", "blocking-modal");
    document.body.append(target, occluder);
    stubHitTest(() => occluder);

    const result = detectOcclusion(target, makeRect(0, 0, 100, 100));

    expect(result.occluded).toBe(true);
    expect(result.reason).toBe("covered");
    expect(result.occluder).toBe(occluder);
  });

  it("ignores tour overlay nodes via the portal root and peels to the target", () => {
    const root = document.createElement("div");
    root.id = "tour-portal-root";
    const overlay = document.createElement("div");
    root.appendChild(overlay);
    const target = document.createElement("div");
    document.body.append(root, target);
    stubHitTest(
      () => overlay,
      () => [overlay, target]
    );

    expect(detectOcclusion(target, makeRect(0, 0, 100, 100)).reason).toBe("ok");
  });

  it("returns offscreen (not occlusion) when the rect is outside the viewport", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const fromPoint = vi.fn(() => target);
    stubHitTest(fromPoint);

    const result = detectOcclusion(target, makeRect(-500, -500, 100, 100));

    expect(result.reason).toBe("offscreen");
    expect(fromPoint).not.toHaveBeenCalled();
  });

  it("honors minVisibleRatio for partial occlusion", () => {
    const target = document.createElement("div");
    const occluder = document.createElement("div");
    document.body.append(target, occluder);
    // Top half (y < 50) shows the target; bottom half + center are covered.
    // Sample points: center (50,50)→occluder, (25,25)+(75,25)→target, (25,75)+(75,75)→occluder → 2/5 visible.
    stubHitTest((_x, y) => (y < 50 ? target : occluder));

    expect(detectOcclusion(target, makeRect(0, 0, 100, 100)).occluded).toBe(true); // 0.4 < default 0.5
    expect(detectOcclusion(target, makeRect(0, 0, 100, 100), { minVisibleRatio: 0.3 }).occluded).toBe(false); // 0.4 ≥ 0.3
  });
});

describe("describeOccluder", () => {
  it("prefers data-tour-id, then role/label, then a tag chain", () => {
    const withTourId = document.createElement("div");
    withTourId.setAttribute("data-tour-id", "blocking-modal");
    expect(describeOccluder(withTourId)).toBe("data-tour-id=blocking-modal");

    const withRole = document.createElement("div");
    withRole.setAttribute("role", "dialog");
    withRole.setAttribute("aria-label", "Trace Input Content");
    expect(describeOccluder(withRole)).toBe("role=dialog label=Trace Input Content");

    const plain = document.createElement("section");
    plain.id = "panel";
    plain.classList.add("drawer", "open");
    expect(describeOccluder(plain)).toBe("section#panel.drawer");

    expect(describeOccluder(null)).toBe("unknown");
  });
});
