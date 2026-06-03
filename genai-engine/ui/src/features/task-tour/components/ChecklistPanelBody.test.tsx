import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TASK_TOUR_SECTIONS } from "../data";

import { ChecklistPanelBody, type ChecklistPanelBodyProps } from "./ChecklistPanelBody";

const SECTION_WITH_STEPS_INDEX = TASK_TOUR_SECTIONS.findIndex((section) => section.items.length > 0);

function renderPanel(overrides: Partial<ChecklistPanelBodyProps> = {}) {
  const props: ChecklistPanelBodyProps = {
    currentSectionIndex: SECTION_WITH_STEPS_INDEX,
    currentItemIndex: 0,
    activeStepContent: "Full instruction copy",
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

  render(<ChecklistPanelBody {...props} />);
  return props;
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
});
