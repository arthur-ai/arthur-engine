import { cleanup, render, screen } from "@testing-library/react";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { storeRecipientName } from "../recipientName";

import { CertificateWidget } from "./CertificateWidget";

import { createTourEngine, TourProvider } from "@/features/tour";

vi.mock("@arthur/shared-components", () => ({
  downloadFile: vi.fn(),
}));

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
  });

  it("shows the certificate only after the tour completes", () => {
    const engine = renderWidget();

    expect(screen.queryByRole("dialog", { name: /certificate of achievement/i })).toBeNull();

    act(() => {
      engine.bus.emit("tour:end", { tourId: "task-tour", reason: "completed" });
    });

    expect(screen.getByRole("dialog", { name: /certificate of achievement/i })).toBeTruthy();
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
});
