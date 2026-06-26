import { createTourEngine, TourProvider } from "@arthur/shared-components/tour";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { storeRecipientName } from "../recipientName";

import { CertificateWidget } from "./CertificateWidget";

import { track } from "@/services/analytics";

vi.mock("@arthur/shared-components", () => ({
  downloadFile: vi.fn(),
}));

vi.mock("@/services/analytics", async (importActual) => {
  const actual = await importActual<typeof import("@/services/analytics")>();
  return { ...actual, track: vi.fn() };
});

// jsdom in this project ships a non-functional `localStorage` stub, so install
// a fresh in-memory implementation per test.
function installMemoryStorage() {
  const store = new Map<string, string>();
  const mock: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => Array.from(store.keys())[index] ?? null,
    removeItem: (key) => void store.delete(key),
    setItem: (key, value) => void store.set(key, String(value)),
  };
  Object.defineProperty(window, "localStorage", { configurable: true, writable: true, value: mock });
}

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
  beforeEach(() => {
    installMemoryStorage();
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("shows the certificate only after the tour completes", () => {
    const engine = renderWidget();

    expect(screen.queryByRole("dialog", { name: /certificate of achievement/i })).toBeNull();

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "completed" });
    });

    expect(screen.getByRole("dialog", { name: /certificate of achievement/i })).toBeTruthy();
  });

  it("tracks a certificate view when the tour completes", () => {
    const engine = renderWidget();

    expect(track).not.toHaveBeenCalledWith("onboarding/wizard_certificate_viewed", expect.anything());

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "completed" });
    });

    expect(track).toHaveBeenCalledWith("onboarding/wizard_certificate_viewed", { course: "Intro to Evals" });
  });

  it("does not track a view when the tour ends without completing", () => {
    const engine = renderWidget();

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "skipped" });
    });

    expect(track).not.toHaveBeenCalledWith("onboarding/wizard_certificate_viewed", expect.anything());
  });

  it("names the recipient from the stored onboarding name", () => {
    storeRecipientName("Jordan Lee");
    const engine = renderWidget();

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "completed" });
    });

    expect(screen.getByText("Jordan Lee")).toBeTruthy();
  });

  it("falls back to the default recipient when no name is stored", () => {
    const engine = renderWidget();

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "completed" });
    });

    expect(screen.getByText("Alex Rivera")).toBeTruthy();
  });

  it("opens the CTA after the certificate is closed, then closes everything on dismiss", async () => {
    const engine = renderWidget();

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "completed" });
    });

    // Certificate is shown first; CTA is not yet visible.
    expect(screen.getByRole("dialog", { name: /certificate of achievement/i })).toBeTruthy();
    expect(screen.queryByRole("dialog", { name: /zach, the cto at arthur/i })).toBeNull();

    // Closing the certificate advances to the CTA dialog.
    fireEvent.click(screen.getByRole("button", { name: /dismiss certificate/i }));
    expect(screen.queryByRole("dialog", { name: /certificate of achievement/i })).toBeNull();
    expect(screen.getByRole("dialog", { name: /zach, the cto at arthur/i })).toBeTruthy();
    expect(track).toHaveBeenCalledWith("onboarding/wizard_cta_viewed", { course: "Intro to Evals" });

    // Dismissing the CTA ends the sequence (awaiting the exit transition).
    fireEvent.click(screen.getByRole("button", { name: /^dismiss$/i }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /zach, the cto at arthur/i })).toBeNull());
  });
});
