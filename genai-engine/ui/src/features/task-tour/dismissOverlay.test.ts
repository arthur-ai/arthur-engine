import { afterEach, describe, expect, it, vi } from "vitest";

import { dismissOverlay } from "./dismissOverlay";

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("dismissOverlay", () => {
  it("returns false when the element is not inside a dismissible overlay", () => {
    const loose = document.createElement("div");
    document.body.appendChild(loose);

    expect(dismissOverlay(loose)).toBe(false);
    expect(dismissOverlay(null)).toBe(false);
  });

  it("dispatches an Escape keydown that bubbles to the overlay container's handler", () => {
    const modalRoot = document.createElement("div");
    modalRoot.className = "MuiModal-root";
    const dialog = document.createElement("div");
    dialog.setAttribute("role", "dialog");
    const inner = document.createElement("button");
    dialog.appendChild(inner);
    modalRoot.appendChild(dialog);
    document.body.appendChild(modalRoot);

    const onEscape = vi.fn();
    modalRoot.addEventListener("keydown", (e) => {
      if ((e as KeyboardEvent).key === "Escape") onEscape();
    });

    expect(dismissOverlay(inner)).toBe(true);
    expect(onEscape).toHaveBeenCalledTimes(1);
  });

  it("clicks the modal backdrop as a fallback gesture", () => {
    const modalRoot = document.createElement("div");
    modalRoot.className = "MuiModal-root";
    const backdrop = document.createElement("div");
    backdrop.className = "MuiBackdrop-root";
    const dialog = document.createElement("div");
    dialog.setAttribute("role", "dialog");
    modalRoot.append(backdrop, dialog);
    document.body.appendChild(modalRoot);

    const onBackdropClick = vi.fn();
    backdrop.addEventListener("click", onBackdropClick);

    dismissOverlay(dialog);

    expect(onBackdropClick).toHaveBeenCalledTimes(1);
  });

  it("dismisses a drawer surface (no backdrop) via Escape without throwing", () => {
    const drawerRoot = document.createElement("div");
    drawerRoot.className = "MuiDrawer-root";
    const paper = document.createElement("div");
    drawerRoot.appendChild(paper);
    document.body.appendChild(drawerRoot);

    const onEscape = vi.fn();
    drawerRoot.addEventListener("keydown", (e) => {
      if ((e as KeyboardEvent).key === "Escape") onEscape();
    });

    expect(dismissOverlay(paper)).toBe(true);
    expect(onEscape).toHaveBeenCalledTimes(1);
  });
});
