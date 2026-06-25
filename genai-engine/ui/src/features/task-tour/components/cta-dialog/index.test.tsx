import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CtaDialog } from ".";

import { track } from "@/services/analytics";

vi.mock("@/services/analytics", async (importActual) => {
  const actual = await importActual<typeof import("@/services/analytics")>();
  return { ...actual, track: vi.fn() };
});

describe("CtaDialog", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the CTO call-to-action with avatar and copy", () => {
    render(<CtaDialog open onDismiss={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: /zach, the cto at arthur/i })).toBeTruthy();
    expect(screen.getByText(/zach fry/i)).toBeTruthy();

    const avatar = screen.getByAltText("Zach Fry") as HTMLImageElement;
    expect(avatar.getAttribute("src")).toBe("/cto-avatar.jpeg");
  });

  it("exposes a booking link that opens in a new tab", () => {
    render(<CtaDialog open onDismiss={vi.fn()} />);

    const bookLink = screen.getByRole("link", { name: /book a time/i });
    expect(bookLink.getAttribute("href")).toBeTruthy();
    expect(bookLink.getAttribute("target")).toBe("_blank");
    expect(bookLink.getAttribute("rel")).toContain("noopener");
  });

  it("tracks a booking click", () => {
    render(<CtaDialog open onDismiss={vi.fn()} />);

    fireEvent.click(screen.getByRole("link", { name: /book a time/i }));

    expect(track).toHaveBeenCalledWith("onboarding/wizard_cta_book_clicked", { course: "Intro to Evals" });
  });

  it("dismisses from the Dismiss button", () => {
    const onDismiss = vi.fn();

    render(<CtaDialog open onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole("button", { name: /^dismiss$/i }));

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("dismisses from the close affordance", () => {
    const onDismiss = vi.fn();

    render(<CtaDialog open onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole("button", { name: /dismiss call to action/i }));

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
