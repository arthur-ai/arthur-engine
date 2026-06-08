import { ThemeProvider } from "@mui/material";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TASK_TOUR_SECTIONS } from "../data";
import type { ChecklistController } from "../hooks/useChecklistController";

import { ChecklistPanelBody } from "./ChecklistPanelBody";

import { lightTheme } from "@/theme/mui-theme";

const SECTION_WITH_STEPS_INDEX = TASK_TOUR_SECTIONS.findIndex((section) => section.items.length > 0);

function renderPanel(overrides: Partial<ChecklistController> = {}) {
  const controller: ChecklistController = {
    isRunning: true,
    isOnStep: true,
    currentSectionIndex: SECTION_WITH_STEPS_INDEX,
    currentItemIndex: 0,
    activeStepContent: "Full instruction copy",
    targetLostHint: null,
    occlusionHint: null,
    onRecoverOcclusion: vi.fn(),
    completedItemKeys: new Set(),
    totalProgress: 0.25,
    onSelectItem: vi.fn(),
    onToggleItem: vi.fn(),
    onSelectSection: vi.fn(),
    onPrevSection: vi.fn(),
    onNextSection: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  };

  render(
    <ThemeProvider theme={lightTheme}>
      <ChecklistPanelBody controller={controller} />
    </ThemeProvider>
  );
  return controller;
}

describe("ChecklistPanelBody", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders the active section title, step title, and instruction copy", () => {
    const section = TASK_TOUR_SECTIONS[SECTION_WITH_STEPS_INDEX];
    renderPanel();

    expect(screen.getByText(section.title)).toBeTruthy();
    expect(screen.getByText(section.items[0].title)).toBeTruthy();
    expect(screen.getByText("Full instruction copy")).toBeTruthy();
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });

  it("dismisses the tour via the hide button", () => {
    const onClose = vi.fn();
    renderPanel({ onClose });

    fireEvent.click(screen.getByRole("button", { name: /hide walkthrough/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("toggles a step's completion without selecting it", () => {
    const onToggleItem = vi.fn();
    const onSelectItem = vi.fn();
    const section = TASK_TOUR_SECTIONS[SECTION_WITH_STEPS_INDEX];
    renderPanel({ onToggleItem, onSelectItem });

    fireEvent.click(screen.getAllByRole("button", { name: /mark step complete/i })[0]);

    expect(onToggleItem).toHaveBeenCalledTimes(1);
    expect(onToggleItem).toHaveBeenCalledWith(section.items[0]);
    expect(onSelectItem).not.toHaveBeenCalled();
  });

  it("renders the occlusion affordance and recovers without selecting the step", () => {
    const onRecoverOcclusion = vi.fn();
    const onSelectItem = vi.fn();
    renderPanel({
      occlusionHint: { message: "Something is covering this step.", actionLabel: "Bring this into view" },
      onRecoverOcclusion,
      onSelectItem,
    });

    expect(screen.getByText("Something is covering this step.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /bring this into view/i }));

    expect(onRecoverOcclusion).toHaveBeenCalledTimes(1);
    expect(onSelectItem).not.toHaveBeenCalled();
  });

  describe("auto-scroll to the highlighted step", () => {
    function rect(partial: Partial<DOMRect>): DOMRect {
      return { x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0, toJSON() {}, ...partial } as DOMRect;
    }

    // jsdom does no layout, so we fake the active row's position relative to a
    // 300px-tall scroll container (top 0, scrollTop 0). Everything that isn't the
    // active row reports the container's rect; the active row reports `activeTop`.
    function mockLayout(activeTop: number) {
      vi.spyOn(Element.prototype, "clientHeight", "get").mockReturnValue(300);
      vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
        if (this.getAttribute("data-active-step") === "true") {
          return rect({ top: activeTop, bottom: activeTop + 60, height: 60 });
        }
        return rect({ top: 0, bottom: 300, height: 300 });
      });
      if (!Element.prototype.scrollTo) {
        Element.prototype.scrollTo = () => {};
      }
      return vi.spyOn(Element.prototype, "scrollTo").mockImplementation(() => {});
    }

    it("scrolls the active row (with its description) into view when it's below the fold", () => {
      const scrollTo = mockLayout(500); // active row sits well below the 300px viewport
      renderPanel({ currentItemIndex: 0 });

      expect(scrollTo).toHaveBeenCalledTimes(1);
      expect(scrollTo).toHaveBeenCalledWith(expect.objectContaining({ behavior: "smooth", top: expect.any(Number) }));
      const { top } = scrollTo.mock.calls[0][0] as ScrollToOptions;
      expect(top).toBeGreaterThan(0);
    });

    it("leaves the scroll position alone when the active row is already fully visible", () => {
      const scrollTo = mockLayout(50); // active row (50–110) fits inside the 0–300 viewport
      renderPanel({ currentItemIndex: 0 });

      expect(scrollTo).not.toHaveBeenCalled();
    });
  });
});
