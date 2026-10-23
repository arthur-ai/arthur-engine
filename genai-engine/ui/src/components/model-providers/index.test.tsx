import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ModelProviders } from "./index";

const mocks = vi.hoisted(() => ({
  permissions: { canRead: true, canWrite: true },
  configuration: vi.fn(),
  remove: vi.fn(),
  refetch: vi.fn(),
}));

vi.mock("./hooks/useGuardrailConfiguration", () => ({
  useGuardrailConfiguration: mocks.configuration,
  useGuardrailPermissions: () => mocks.permissions,
}));
vi.mock("./hooks/useProviders", () => ({
  useProviders: () => ({ data: [{ provider: "openai", enabled: true }] }),
}));
vi.mock("./hooks/useRemoveProvider", () => ({
  useRemoveProvider: () => ({ mutateAsync: mocks.remove, isPending: false }),
}));
vi.mock("./hooks/useSaveProvider", () => ({ useSaveProvider: () => ({ mutateAsync: vi.fn() }) }));
vi.mock("./hooks/useSaveModelWhitelist", () => ({ useSaveModelWhitelist: () => ({ mutateAsync: vi.fn() }) }));
vi.mock("./components/edit-form", () => ({ EditForm: () => null }));
vi.mock("notistack", () => ({ useSnackbar: () => ({ enqueueSnackbar: vi.fn() }) }));

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  mocks.permissions = { canRead: true, canWrite: true };
  mocks.configuration.mockReturnValue({
    data: { guardrail_llm: { provider: "openai", model: "gpt-4o" }, guardrail_llm_status: "configured" },
    refetch: mocks.refetch,
  });
  mocks.remove.mockResolvedValue(undefined);
});

describe("provider guardrail lifecycle warnings", () => {
  it("blocks lifecycle actions until configuration loads and offers retry on failure", () => {
    mocks.configuration.mockReturnValue({ isFetching: true, refetch: mocks.refetch });
    const view = render(<ModelProviders />);
    expect((screen.getByTitle("Delete provider") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTitle("Configure provider") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Loading guardrail settings before changing model providers.")).toBeTruthy();
    mocks.configuration.mockReturnValue({ isError: true, refetch: mocks.refetch });
    view.rerender(<ModelProviders />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(mocks.refetch).toHaveBeenCalledOnce();
    expect((screen.getByTitle("Delete provider") as HTMLButtonElement).disabled).toBe(true);
    expect(mocks.remove).not.toHaveBeenCalled();
  });

  it("warns about guardrails before deleting the selected provider", async () => {
    render(<ModelProviders />);
    fireEvent.click(screen.getByTitle("Delete provider"));
    expect(screen.getByText("Guardrails need a configured model provider. Removing this provider will require configuration.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(mocks.remove).toHaveBeenCalledWith("openai"));
  });

  it("blocks confirmation if the configuration refresh fails while the dialog is open", () => {
    const view = render(<ModelProviders />);
    fireEvent.click(screen.getByTitle("Delete provider"));
    mocks.configuration.mockReturnValue({ isError: true, refetch: mocks.refetch });
    view.rerender(<ModelProviders />);
    expect((screen.getByRole("button", { name: "Delete" }) as HTMLButtonElement).disabled).toBe(true);
    expect(mocks.remove).not.toHaveBeenCalled();
  });

  it("does not expand lifecycle permissions for a read-only selected provider", () => {
    mocks.permissions.canWrite = false;
    render(<ModelProviders />);
    expect((screen.getByTitle("Delete provider") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTitle("Configure provider") as HTMLButtonElement).disabled).toBe(true);
  });

  it("does not block unrelated provider administration without configuration-read permission", () => {
    mocks.permissions = { canRead: false, canWrite: false };
    mocks.configuration.mockReturnValue({});
    render(<ModelProviders />);
    expect((screen.getByTitle("Delete provider") as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByTitle("Configure provider") as HTMLButtonElement).disabled).toBe(false);
  });
});
