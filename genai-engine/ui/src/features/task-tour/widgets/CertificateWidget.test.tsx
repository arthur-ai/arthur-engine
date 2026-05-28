import { cleanup, render, screen } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CertificateWidget } from "./CertificateWidget";

import { createTourEngine, TourProvider } from "@/features/tour";

vi.mock("@arthur/shared-components", () => ({
  downloadFile: vi.fn(),
}));

function renderWidget() {
  const engine = createTourEngine({
    config: {
      id: "task-tour",
      sections: [],
    },
  });

  render(
    <TourProvider tour={engine}>
      <CertificateWidget />
    </TourProvider>
  );

  return engine;
}

describe("CertificateWidget", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows the certificate only after the tour completes", () => {
    const engine = renderWidget();

    expect(screen.queryByRole("dialog", { name: /certificate of achievement/i })).toBeNull();

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "completed" });
    });

    expect(screen.getByRole("dialog", { name: /certificate of achievement/i })).toBeTruthy();
  });
});
