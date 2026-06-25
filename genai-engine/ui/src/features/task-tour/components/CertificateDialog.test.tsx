import { downloadFile } from "@arthur/shared-components";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CertificateDialog } from "./CertificateDialog";

import { track } from "@/services/analytics";

vi.mock("@arthur/shared-components", () => ({
  downloadFile: vi.fn(),
}));

vi.mock("@/services/analytics", async (importActual) => {
  const actual = await importActual<typeof import("@/services/analytics")>();
  return { ...actual, track: vi.fn() };
});

// Mirror the real capture library: `useToBlob`'s `onSuccess` receives a real
// `Blob` (not the data-URL *string* `toPng` would yield) — the regression this
// test guards. The trigger (2nd tuple slot) fires that callback.
vi.mock("@hugocxl/react-to-image", () => {
  const makeHook = (payload: unknown) => (options?: { onSuccess?: (data: unknown) => void }) => {
    const trigger = () => options?.onSuccess?.(payload);
    return [{ status: "idle" }, trigger, () => {}];
  };
  return {
    useToBlob: makeHook(new Blob([new Uint8Array([137, 80, 78, 71])], { type: "image/png" })),
  };
});

describe("CertificateDialog", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("downloads a real PNG blob, not the data-URL string", () => {
    render(<CertificateDialog open onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /download png/i }));

    expect(downloadFile).toHaveBeenCalledWith(expect.any(Blob), "certificate.png", "image/png");
    expect(track).toHaveBeenCalledWith("onboarding/wizard_certificate_download_clicked", { course: "Intro to Evals" });
  });

  it("tracks share clicks by destination", () => {
    render(<CertificateDialog open onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("link", { name: /share to linkedin/i }));
    expect(track).toHaveBeenCalledWith("onboarding/wizard_certificate_share_clicked", {
      destination: "linkedin",
      course: "Intro to Evals",
    });

    fireEvent.click(screen.getByRole("link", { name: /share to x/i }));
    expect(track).toHaveBeenCalledWith("onboarding/wizard_certificate_share_clicked", { destination: "x", course: "Intro to Evals" });
  });

  it("renders the achievement certificate design and sharing actions", () => {
    render(<CertificateDialog open recipientName="Alex Rivera" issuedOn="May 27, 2026" onClose={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: /certificate of achievement/i })).toBeTruthy();
    expect(screen.getByText("Arthur AI · Intro to Evals")).toBeTruthy();
    expect(screen.getByText("THIS IS TO CERTIFY THAT")).toBeTruthy();
    expect(screen.getByText("Alex Rivera")).toBeTruthy();
    expect(screen.getByText("May 27, 2026")).toBeTruthy();
    expect(screen.getByRole("button", { name: /download png/i })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /download pdf/i })).toBeNull();
    expect(screen.getByRole("link", { name: /share to linkedin/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /share to x/i })).toBeTruthy();
  });

  it("dismisses from the close affordance and tracks the method", () => {
    const onClose = vi.fn();

    render(<CertificateDialog open onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /dismiss certificate/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith("onboarding/wizard_certificate_closed", { method: "dismiss", course: "Intro to Evals" });
  });

  it("advances from a visible primary action button and tracks the method", () => {
    const onClose = vi.fn();

    render(<CertificateDialog open onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith("onboarding/wizard_certificate_closed", { method: "continue", course: "Intro to Evals" });
  });
});
