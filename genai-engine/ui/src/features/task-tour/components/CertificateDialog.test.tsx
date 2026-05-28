import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CertificateDialog } from "./CertificateDialog";

vi.mock("@arthur/shared-components", () => ({
  downloadFile: vi.fn(),
}));

describe("CertificateDialog", () => {
  afterEach(() => {
    cleanup();
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

  it("dismisses from the close affordance", () => {
    const onClose = vi.fn();

    render(<CertificateDialog open onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /dismiss certificate/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
