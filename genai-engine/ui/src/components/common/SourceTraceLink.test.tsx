import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SourceTraceLink, traceDeepLinkPath } from "./SourceTraceLink";

afterEach(cleanup);

const VARIANTS = ["subtle", "field", "pill"] as const;

const renderLink = (variant: (typeof VARIANTS)[number], onOpen?: () => void) => {
  const onAncestorClick = vi.fn();

  render(
    <MemoryRouter>
      <div onClick={onAncestorClick}>
        <SourceTraceLink variant={variant} taskId="task-1" traceId="trace-1" onOpen={onOpen} />
      </div>
    </MemoryRouter>
  );

  return { link: screen.getByRole("link"), onAncestorClick };
};

describe.each(VARIANTS)("SourceTraceLink (%s)", (variant) => {
  it("opens in place on plain click when onOpen is provided", () => {
    const onOpen = vi.fn();
    const { link, onAncestorClick } = renderLink(variant, onOpen);

    const notPrevented = fireEvent.click(link);

    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(notPrevented).toBe(false);
    expect(onAncestorClick).not.toHaveBeenCalled();
  });

  it("keeps native new-tab behavior on modifier click", () => {
    const onOpen = vi.fn();
    const { link, onAncestorClick } = renderLink(variant, onOpen);

    const notPrevented = fireEvent.click(link, { metaKey: true });

    expect(onOpen).not.toHaveBeenCalled();
    expect(notPrevented).toBe(true);
    expect(onAncestorClick).not.toHaveBeenCalled();
  });

  it("keeps the new-tab link behavior when onOpen is not provided", () => {
    const { link, onAncestorClick } = renderLink(variant);

    const notPrevented = fireEvent.click(link);

    expect(notPrevented).toBe(true);
    expect(onAncestorClick).not.toHaveBeenCalled();
    expect(link.getAttribute("href")).toBe(traceDeepLinkPath("task-1", "trace-1"));
    expect(link.getAttribute("target")).toBe("_blank");
  });
});
