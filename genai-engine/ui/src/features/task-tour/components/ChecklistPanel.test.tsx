import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TASK_TOUR_SECTIONS } from "../data";

import { ChecklistPanel, type ChecklistPanelProps } from "./ChecklistPanel";

const SECTION_WITH_STEPS_INDEX = TASK_TOUR_SECTIONS.findIndex((section) => section.items.length > 0);

function renderPanel(overrides: Partial<ChecklistPanelProps> = {}) {
  const props: ChecklistPanelProps = {
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

  render(<ChecklistPanel {...props} />);
  return props;
}

describe("ChecklistPanel minimized mode", () => {
  afterEach(() => {
    cleanup();
  });

  it("minimizes without dismissing the tour", () => {
    const onMinimize = vi.fn();

    renderPanel({ onMinimize });

    fireEvent.click(screen.getByRole("button", { name: /minimize walkthrough/i }));

    expect(onMinimize).toHaveBeenCalledTimes(1);
  });

  it("shows only the active step title and progress when minimized", () => {
    const onExpand = vi.fn();
    const activeStepTitle = TASK_TOUR_SECTIONS[SECTION_WITH_STEPS_INDEX].items[0].title;

    renderPanel({ isMinimized: true, onExpand });

    expect(screen.getByText(activeStepTitle)).toBeTruthy();
    expect(screen.getByRole("progressbar")).toBeTruthy();
    expect(screen.queryByText("Full instruction copy")).toBeNull();
    expect(screen.queryByText(TASK_TOUR_SECTIONS[SECTION_WITH_STEPS_INDEX].title)).toBeNull();
    expect(screen.queryByRole("button", { name: /hide walkthrough/i })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /expand walkthrough/i }));

    expect(onExpand).toHaveBeenCalledTimes(1);
  });
});
